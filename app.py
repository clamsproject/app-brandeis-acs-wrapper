import argparse
import os
import tempfile
from typing import Dict, Union

import bacs
from clams import ClamsApp, Restifier
from mmif import DocumentTypes, AnnotationTypes, Mmif, Document, View, Annotation

__version__ = '0.3.2'


class Segmenter(ClamsApp):
    PATH_ESCAPER = '+'
    SEGMENTER_ACCEPTED_EXTENSIONS = {'.mp3', '.wav'}
    TIME_FRAME_PREFIX = 'tf'

    def _appmetadata(self) -> dict:
        return {
            "name": "Brandeis Acoustic Classification & Segmentation tool",
            "description": "tbd",
            "vendor": "Team CLAMS",
            "iri": f"http://mmif.clams.ai/apps/brandeis-acs/{__version__}",
            "requires": [DocumentTypes.AudioDocument.value],
            "produces": [
                AnnotationTypes.TimeFrame.value
            ]
        }

    def _annotate(self, mmif: Union[str, dict, Mmif], save_tsv=False, pretty=False) -> Mmif:
        mmif_obj: Mmif
        if isinstance(mmif, Mmif):
            mmif_obj: Mmif = mmif
        else:
            mmif_obj: Mmif = Mmif(mmif)

        # get AudioDocuments with locations
        docs = [document for document in mmif_obj.documents
                if document.at_type == DocumentTypes.AudioDocument.value
                and len(document.location) > 0
                and os.path.splitext(document.location)[-1] in self.SEGMENTER_ACCEPTED_EXTENSIONS]

        files = [document.location_path() for document in docs]

        # key them by location
        docs_dict: Dict[str, Document] = {self.escape_filepath(doc.location_path()): doc for doc in docs}

        segmented, lengths = self.segment(files, save_tsv)

        for filename, segmented_audio, total_frames in zip(files, segmented, lengths):

            v: View = mmif_obj.new_view()
            self.stamp_view(v, docs_dict[self.escape_filepath(filename)].id)

            tf_idx = 1

            speech_starts = sorted(segmented_audio.keys())
            if speech_starts[0] > 0:
                self.create_segment_tf(0, speech_starts[0] - 1, tf_idx, 'non-speech')
                tf_idx += 1
            nonspeech_start = None
            for speech_start in speech_starts:
                if nonspeech_start is not None:
                    nonspeech_end = speech_start - 1
                    v.add_annotation(
                        self.create_segment_tf(nonspeech_start, nonspeech_end, tf_idx, 'non-speech')
                    )
                    tf_idx += 1
                speech_end = segmented_audio[speech_start]
                nonspeech_start = speech_end + 1
                v.add_annotation(
                    self.create_segment_tf(speech_start, speech_end, tf_idx, 'speech')
                )
                tf_idx += 1

            if nonspeech_start < total_frames:
                v.add_annotation(
                    self.create_segment_tf(nonspeech_start, total_frames, tf_idx, 'non-speech')
                )
        return mmif_obj

    def escape_filepath(self, path):
        return path.replace(os.sep, self.PATH_ESCAPER)

    def create_segment_tf(self, start: float, end: float, index: int, frame_type: str) -> Annotation:
        assert frame_type in {'speech', 'non-speech'}
        tf = Annotation()
        tf.at_type = AnnotationTypes.TimeFrame.value
        tf.id = self.TIME_FRAME_PREFIX + str(index)
        # times should be passed in milliseconds
        tf.properties['start'] = start
        tf.properties['end'] = end
        tf.properties['frameType'] = frame_type
        return tf

    def stamp_view(self, view: View, tf_source_id: str):
        if view.is_frozen():
            raise ValueError("can't modify an old view")
        view.metadata['app'] = self.metadata['iri']
        view.new_contain(AnnotationTypes.TimeFrame.value, {'unit': 'milliseconds', 'document': tf_source_id})

    def segment(self, files: list, save_tsv=False) -> (list, list):
        temp_dir = tempfile.TemporaryDirectory()
        segmented = []
        audio_length = []
        for f in files:
            if os.path.exists(f):
                os.symlink(f, os.path.join(temp_dir.name, self.escape_filepath(f)))
            else:
                raise FileNotFoundError(f)

        model = bacs.classifier.load_model(bacs.defmodel_path)
        for wav in bacs.reader.read_audios(temp_dir.name):
            predicted = bacs.classifier.predict_pipeline(wav, model)
            smoothed = bacs.smoothing.smooth(predicted)
            speech_portions, total_frames = bacs.writer.index_frames(smoothed)
            if save_tsv:
                bacs.writer.print_durations(speech_portions, os.path.join(*wav), total_frames)
            speech_portions_in_ms = {}
            ms_multiplier = bacs.feature.FRAME_SIZE
            for s, e in speech_portions.items():
                speech_portions_in_ms[s * ms_multiplier] = e * ms_multiplier
            segmented.append(speech_portions_in_ms)
            audio_length.append(total_frames * ms_multiplier)
        temp_dir.cleanup()
        return segmented, audio_length


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--once',
                        type=str,
                        metavar='PATH',
                        help='Use this flag if you want to run the segmenter on a path you specify, instead of running '
                             'the Flask app.')
    parser.add_argument('--pretty',
                        action='store_true',
                        help='Use this flag to return "pretty" (indented) MMIF data.')
    parser.add_argument('--save-tsv',
                        action='store_true',
                        help='Use this flag to preserve the intermediary TSV file '
                             'generated by the segmenter.')

    parsed_args = parser.parse_args()

    if parsed_args.once:
        with open(parsed_args.once) as mmif_in:
            mmif_str = mmif_in.read()

        segmenter_app = Segmenter()

        mmif_out = segmenter_app.annotate(mmif_str, save_tsv=parsed_args.save_tsv, pretty=parsed_args.pretty)
        with open('mmif_out.json', 'w') as out_file:
            out_file.write(mmif_out)
    else:
        segmenter_app = Segmenter()
        segmenter_service = Restifier(segmenter_app)
        segmenter_service.run()
