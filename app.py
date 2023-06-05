import argparse
import os
import tempfile
from typing import Union, Dict

import bacs
from clams import ClamsApp, Restifier
from mmif import Mmif, View, Document, AnnotationTypes, DocumentTypes

import metadata


class BrandeisAcs(ClamsApp):
    PATH_ESCAPER = '+'
    SEGMENTER_ACCEPTED_EXTENSIONS = {'.mp3', '.wav'}

    def _appmetadata(self):
        pass

    def _annotate(self, mmif: Union[str, dict, Mmif], **parameters) -> Mmif:
        if not isinstance(mmif, Mmif):
            mmif = Mmif(mmif)
        config = self.get_configuration(**parameters)

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
                          timeUnit=metadata.timeunit,
                          document=docs_dict[self.escape_filepath(filename)].id)

            speech_starts = sorted(segmented_audio.keys())
            if speech_starts[0] > 0:
                v.new_annotation(AnnotationTypes.TimeFrame, start=0, end=speech_starts[0] - 1, frameType='non-speech')
            nonspeech_start = None
            for speech_start in speech_starts:
                if nonspeech_start is not None:
                    nonspeech_end = speech_start - 1
                    v.new_annotation(AnnotationTypes.TimeFrame, start=nonspeech_start, end=nonspeech_end, frameType='non-speech')
                speech_end = segmented_audio[speech_start]
                nonspeech_start = speech_end + 1
                v.new_annotation(AnnotationTypes.TimeFrame, start=speech_start, end=speech_end, frameType='speech')
            if nonspeech_start < total_frames:
                v.new_annotation(AnnotationTypes.TimeFrame, start=nonspeech_start, end=total_frames, frameType='non-speech')
        return mmif

    def escape_filepath(self, path):
        return path.replace(os.sep, self.PATH_ESCAPER)

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", action="store", default="5000", help="set port to listen"
    )
    parser.add_argument("--production", action="store_true", help="run gunicorn server")
    # more arguments as needed
    # parser.add_argument(more_arg...)

    parsed_args = parser.parse_args()

    # create the app instance
    app = BrandeisAcs()

    http_app = Restifier(app, port=int(parsed_args.port)
    )
    if parsed_args.production:
        http_app.serve_production()
    else:
        http_app.run()
