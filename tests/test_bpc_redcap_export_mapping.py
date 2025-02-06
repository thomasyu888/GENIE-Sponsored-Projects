import logging
import pytest
from unittest import mock

import pandas as pd
import synapseclient

from geniesp import bpc_redcap_export_mapping as bpc_export

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def mock_syn():
    yield mock.Mock(spec=synapseclient.Synapse)


def test_that_get_drug_variable_names_gets_expected_list():
    var_names = bpc_export.get_drug_variable_names()
    assert var_names == [
        "drugs_drug_1",
        "drugs_drug_oth1",
        "drugs_drug_2",
        "drugs_drug_oth2",
        "drugs_drug_3",
        "drugs_drug_oth3",
        "drugs_drug_4",
        "drugs_drug_oth4",
        "drugs_drug_5",
        "drugs_drug_oth5",
    ]


def test_get_mapping_data_calls_grs_if_use_grs_is_true(mock_syn):
    with mock.patch.object(mock_syn, "get") as mock_get, mock.patch.object(
        pd, "read_csv"
    ):
        bpc_export.get_mapping_data(
            syn=mock_syn, synid_file_grs="synGRS", synid_file_dd="synDD", use_grs=True
        )
        mock_get.assert_called_with("synGRS")


def test_get_mapping_data_calls_dd_if_use_grs_is_false(mock_syn):
    with mock.patch.object(mock_syn, "get") as mock_get, mock.patch.object(
        pd, "read_csv"
    ):
        bpc_export.get_mapping_data(
            syn=mock_syn, synid_file_grs="synGRS", synid_file_dd="synDD", use_grs=False
        )
        mock_get.assert_called_with("synDD")


@pytest.mark.parametrize(
    "input_mapping, var_names, output_mapping",
    [
        (
            pd.DataFrame(
                {
                    "Variable / Field Name": ["drugs_drug_1", "drugs_drug_2"],
                    "Choices, Calculations, OR Slider Labels": [
                        "D001, Aspirin | D002, Ibuprofen | D003, Paracetamol",
                        "D004, Tylenol |",
                    ],
                }
            ),
            ["drugs_drug_1", "drugs_drug_2"],
            {
                "Aspirin": "D001",
                "Ibuprofen": "D002",
                "Paracetamol": "D003",
                "Tylenol": "D004",
            },
        ),
        (
            pd.DataFrame(
                {
                    "Variable / Field Name": ["drugs_drug_1"],
                    "Choices, Calculations, OR Slider Labels": ["D001, Aspirin|"],
                }
            ),
            ["drugs_drug_1"],
            {"Aspirin": "D001"},
        ),
        (
            pd.DataFrame(
                {
                    "Variable / Field Name": ["ethnicity"],
                    "Choices, Calculations, OR Slider Labels": ["1"],
                }
            ),
            ["drugs_drug_1"],
            {},
        ),
        (
            pd.DataFrame(
                {
                    "Variable / Field Name": ["drugs_drug_1"],
                    "Choices, Calculations, OR Slider Labels": [
                        "D001, Aspirin (alternative) | D002, Ibuprofen | D003, Paracetamol"
                    ],
                    "extra_column": ["test1"],
                }
            ),
            ["drugs_drug_1"],
            {"Aspirin": "D001", "Ibuprofen": "D002", "Paracetamol": "D003"},
        ),
    ],
    ids=[
        "multiple_drug_vars",
        "empty_split",
        "nothing_to_parse",
        "parenthesis_split",
    ],
)
def test_that_parse_drug_mappings(input_mapping, var_names, output_mapping):
    result = bpc_export.parse_drug_mappings(mapping=input_mapping, var_names=var_names)
    assert result == output_mapping


@pytest.mark.parametrize(
    "input_data, oncotree_dict, expected_warning",
    [
        (
            pd.DataFrame(
                dict(
                    ONCOTREE_CODE=["Renal Cell Carcinoma", "Renal Clear Cell Carcinoma"]
                )
            ),
            {
                "RCC": {"CANCER_TYPE": "Renal Cell Carcinoma"},
                "OVARY": {"CANCER_TYPE": "Ovarian Cancer"},
            },
            "There are invalid values in ONCOTREE_CODE column in the clinical df: ['Renal Cell Carcinoma', 'Renal Clear Cell Carcinoma']",
        ),
        (
            pd.DataFrame(dict(ONCOTREE_CODE=["Renal Cell Carcinoma", "RCC"])),
            {
                "RCC": {"CANCER_TYPE": "Renal Cell Carcinoma"},
                "OVARY": {"CANCER_TYPE": "Ovarian Cancer"},
            },
            "There are invalid values in ONCOTREE_CODE column in the clinical df: ['Renal Cell Carcinoma']",
        ),
    ],
    ids=["all_invalid", "some_invalid"],
)
def test_that_check_oncotree_codes_gives_expected_warning_when_invalid_codes(
    caplog, input_data, oncotree_dict, expected_warning
):
    with caplog.at_level(logging.WARNING):
        bpc_export.check_oncotree_codes(df=input_data, oncotree_dict=oncotree_dict)
    assert expected_warning in caplog.text


def test_that_check_oncotree_codes_gives_no_warning_when_all_codes_valid(caplog):
    input_data = pd.DataFrame(dict(ONCOTREE_CODE=["RCC", "OVARY"]))
    oncotree_dict = {
        "RCC": {"CANCER_TYPE": "Renal Cell Carcinoma"},
        "OVARY": {"CANCER_TYPE": "Ovarian Cancer"},
    }
    with caplog.at_level(logging.WARNING):
        bpc_export.check_oncotree_codes(df=input_data, oncotree_dict=oncotree_dict)
    assert (
        "There are invalid values in ONCOTREE_CODE column in the clinical df"
        not in caplog.text
    )
