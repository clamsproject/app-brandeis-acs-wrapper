import argparse
import os
import tempfile
from typing import Dict, Union

import bacs
from clams import ClamsApp, Restifier, AppMetadata
from mmif import DocumentTypes, AnnotationTypes, Mmif, Document, View

__version__ = '0.3.4'


class BACS(ClamsApp):
    PATH_ESCAPER = '+'
    SEGMENTER_ACCEPTED_EXTENSIONS = {'.mp3', '.wav'}
    TIME_FRAME_PREFIX = 'tf'

    def _appmetadata(self):
        metadata = AppMetadata(
            name="Brandeis ACS Wrapper",
            description="Brandeis Acoustic Classification & Segmentation (ACS) is a audio segmentation tool developed "
                        "at Brandeis Lab for Linguistics and Computation. "
                        "The original software can be found at "
                        "https://github.com/brandeis-llc/acoustic-classification-segmentation .",
            app_version=__version__,
            wrappee_version='0.1.10',
            wrappee_license='Apache2.0',
            license='Apache2.0',
            identifier=f"http://apps.clams.ai/brandeis-acs-wrapper/{__version__}",
        )
        metadata.add_input(DocumentTypes.AudioDocument)
        metadata.add_output(AnnotationTypes.TimeFrame)
        return metadata

    def _annotate(self, mmif: Union[str, dict, Mmif], **kwargs) -> Mmif:
        if not isinstance(mmif, Mmif):
            mmif = Mmif(mmif)
        config = self.get_configuration(**kwargs)

        # get AudioDocuments with locations
        docs = [document for document in mmif.documents
                if document.at_type == DocumentTypes.AudioDocument
                and len(document.location) > 0
                and os.path.splitext(document.location)[-1] in self.SEGMENTER_ACCEPTED_EXTENSIONS]

        files = [document.location_path() for document in docs]

        # key them by location
        docs_dict: Dict[str, Document] = {self.escape_filepath(doc.location_path()): doc for doc in docs}

        segmented, lengths = self.run_bacs(files)

        for filename, segmented_audio, total_frames in zip(files, segmented, lengths):

            v: View = mmif.new_view()
            self.sign_view(v, config)
            v.new_contain(AnnotationTypes.TimeFrame,
                          timeUnit='milliseconds',
                          document=docs_dict[self.escape_filepath(filename)].id)

            speech_starts = sorted(segmented_audio.keys())
            if speech_starts[0] > 0:
                self.create_segment_tf(v, 0, speech_starts[0] - 1, 'non-speech')
            nonspeech_start = None
            for speech_start in speech_starts:
                if nonspeech_start is not None:
                    nonspeech_end = speech_start - 1
                    self.create_segment_tf(v, nonspeech_start, nonspeech_end, 'non-speech')
                speech_end = segmented_audio[speech_start]
                nonspeech_start = speech_end + 1
                self.create_segment_tf(v, speech_start, speech_end, 'speech')

            if nonspeech_start < total_frames:
                self.create_segment_tf(v, nonspeech_start, total_frames, 'non-speech')
        return mmif

    def escape_filepath(self, path):
        return path.replace(os.sep, self.PATH_ESCAPER)

    @staticmethod
    def create_segment_tf(parent_view: View, start: float, end: float, frame_type: str) -> None:
        assert frame_type in {'speech', 'non-speech'}
        tf = parent_view.new_annotation(AnnotationTypes.TimeFrame)
        # times should be passed in milliseconds
        tf.add_property('start', start)
        tf.add_property('end', end)
        tf.add_property('frameType', frame_type)

    def run_bacs(self, files: list) -> (list, list):
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
    parser.add_argument('--production',
                        action='store_true')
    parsed_args = parser.parse_args()

    segmenter_app = BACS()
    segmenter_service = Restifier(segmenter_app)
    if parsed_args.production:
        segmenter_service.serve_production()
    else:
        segmenter_service.run()
