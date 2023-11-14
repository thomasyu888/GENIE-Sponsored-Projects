"""GENIE SP/BPC cBioPortal exporter CLI"""
import argparse
import logging
import os

import pandas as pd
import synapseclient
from genie import process_functions


from geniesp.bpc_redcap_export_mapping import get_survival_info
from geniesp.config import Brca, Crc, Nsclc, Panc, Prostate, Bladder
from geniesp.extract import Extract
from geniesp.transforms import (
    TimelinePerformanceTransform,
    TimelineTreatmentRadTransform,
    TimelineTreatmentTransform,
    TimelineTransform,
    TimelineSampleTransform,
    TimelineSequenceTransform,
    TimelineDxTransform,
    SurvivalTransform,
    SurvivalTreatmentTransform,
    SampleTransform,
    PatientTransform
)
from geniesp.runner import write_and_storedf, write_clinical_file


BPC_MAPPING = {
    "NSCLC": Nsclc,
    "CRC": Crc,
    "BrCa": Brca,
    "PANC": Panc,
    "Prostate": Prostate,
    "BLADDER": Bladder
}


def build_parser():
    parser = argparse.ArgumentParser(description="Run GENIE sponsored projects")
    parser.add_argument(
        "sp",
        type=str,
        help="Specify sponsored project to run",
        choices=BPC_MAPPING.keys(),
    )

    parser.add_argument("release", type=str, help="Specify bpc release")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload files into Synapse BPC staging directory. Default: false.",
    )
    parser.add_argument(
        "--log",
        "-l",
        type=str,
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Set logging output level " "(default: %(default)s)",
    )
    parser.add_argument(
        "--cbioportal",
        type=str,
        help="Optional parameter to specify cbioportal folder location",
    )
    return parser.parse_args()

def main():
    """Main"""
    args = build_parser()

    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: args.log")
    logging.basicConfig(level=numeric_level)

    syn = synapseclient.login()

    if args.cbioportal is None:
        cbiopath = "../cbioportal"
    else:
        cbiopath = args.cbioportal

    config = BPC_MAPPING[args.sp]

    timeline_files = {
        "TIMELINE-PERFORMANCE": TimelinePerformanceTransform,
        "TIMELINE-TREATMENT-RT":  TimelineTreatmentRadTransform,
        "TIMELINE-DX": TimelineDxTransform,
        "TIMELINE-IMAGING": TimelineTransform,
        "TIMELINE-MEDONC": TimelineTransform,
        "TIMELINE-PATHOLOGY": TimelineTransform,
        "TIMELINE-SAMPLE": TimelineSampleTransform,
        "TIMELINE-SEQUENCE": TimelineSequenceTransform,
        "TIMELINE-LAB": TimelineTransform,
        "SURVIVAL": SurvivalTransform,
        "REGIMEN": SurvivalTreatmentTransform,
        "SAMPLE": SampleTransform,
        "PATIENT": PatientTransform,

    }
    # Exception for timeline treatment file
    temp_extract = Extract(
        bpc_config = config,
        sample_type = "TIMELINE-TREATMENT",
        syn = syn
    )
    temp_transform = TimelineTreatmentTransform(
        extract = temp_extract,
        bpc_config = config
    )

    timeline_treatment_df = temp_transform.create_timeline_file()
    survival_info = get_survival_info(
        syn,
        temp_extract.mapping_df,
        temp_extract.data_tables_df,
        config.cohort,
        config.prissmm_synid
    )

    for sample_type, transform_cls in timeline_files.items():
        # Conditions to skip
        if sample_type == "TIMELINE-LAB" and args.sp in ["NSCLC", "BLADDER"]:
            continue
        if sample_type == "TIMELINE-PERFORMANCE" and args.sp not in ['BLADDER']:
            continue
        if sample_type == "TIMELINE-TREATMENT-RT" and args.sp in ["BrCa", "CRC"]:
            continue

        # Download all the files required for processing
        temp_extract = Extract(
            bpc_config = config,
            sample_type = sample_type,
            syn = syn
        )
        derived_variables = temp_extract.get_derived_variable_files()
        # Leverage the cbioportal mapping and derived variables to create the timeline files
        temp_transform = transform_cls(
            # timeline_infodf= temp_extract.timeline_infodf,
            extract = temp_extract,
            bpc_config = config
        )
        if sample_type == 'TIMELINE-DX':
            filter_start = False
        else:
            filter_start = True

        performance_data = temp_transform.create_timeline_file(filter_start=filter_start)
        # This is specific to the timeline treatment file where it is concatenated with
        # the timeline file
        if sample_type == "TIMELINE-TREATMENT-RT":
            performance_data = pd.concat(
                [timeline_treatment_df, performance_data]
            )
        # store the files with provenance
        # Generate provenance
        used_entities = [
            config.redcap_to_cbio_mapping_synid,
            config.data_tables_id,
            config.mg_release_synid,
            config.prissmm_synid,
            config.sample_retraction_synid,
            config.patient_retraction_synid,
            config.retraction_at_release_synid,
            config.temporary_patient_retraction_synid,
            config.mg_assay_synid,
        ]
        used_entities.extend(derived_variables['used'])
        if sample_type.startswith("TIMELINE"):
            write_and_storedf(
                syn=syn,
                df=performance_data,
                filepath=os.path.join(args.sp, f"{sample_type}.txt"),
                used_entities = used_entities
            )
        else:
            clinical_path = write_clinical_file(
                performance_data,
                survival_info,
                os.path.join(args.sp, f"{sample_type}.txt"),
            )
            ent = synapseclient.File(
                clinical_path, parent="syn52950402"
            )
            ent = syn.store(
                ent, used=used_entities, executed="https://github.com/Sage-Bionetworks/GENIE-Sponsored-Projects"
            )
    # BPC_MAPPING[args.sp](syn, cbiopath, release=args.release, upload=args.upload).run()


if __name__ == "__main__":
    main()
