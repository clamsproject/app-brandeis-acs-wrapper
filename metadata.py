"""
The purpose of this file is to define the metadata of the app with minimal imports. 

DO NOT CHANGE the name of the file
"""
import re
from clams.appmetadata import AppMetadata
from mmif import DocumentTypes, AnnotationTypes


timeunit = 'milliseconds'
# DO NOT CHANGE the function name
def appmetadata() -> AppMetadata:
    """
    Function to set app-metadata values and return it as an ``AppMetadata`` obj.
    Read these documentations before changing the code below
    - https://sdk.clams.ai/appmetadata.html metadata specification. 
    - https://sdk.clams.ai/autodoc/clams.appmetadata.html python API
    :return: AppMetadata object holding all necessary information.
    """

    # first set up some basic information
    metadata = AppMetadata(
        name="Brandeis ACS Wrapper",
        description="Brandeis Acoustic Classification & Segmentation (ACS) is a audio segmentation tool developed "
                    "at Brandeis Lab for Linguistics and Computation. "
                    "The original software can be found at "
                    "https://github.com/brandeis-llc/acoustic-classification-segmentation .",
        url="https://github.com/clamsproject/app-brandeis-acs-wrapper",
        app_license='Apache2.0',
        analyzer_version=
        [l.strip().rsplit('==')[-1] for l in open('requirements.txt').readlines() if re.match(r'^brandeis-acs==', l)][
            0],
        analyzer_license='Apache2.0',
        identifier=f"brandeis-acs-wrapper",
    )

    metadata.add_input(DocumentTypes.AudioDocument)
    metadata.add_output(AnnotationTypes.TimeFrame, timeunit=timeunit)

    return metadata


# DO NOT CHANGE the main block
if __name__ == '__main__':
    import sys

    sys.stdout.write(appmetadata().jsonify(pretty=True))
