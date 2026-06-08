"""Shared medication/supplement schedule metadata for admin and PDF state.

Historical dose observations live as ``SourceEvent`` records. This module only
contains display metadata so rendered month state can show the current regimen.
"""

from __future__ import annotations

from packages.core.models import MedicationGroup, MedicationItem


def default_medication_groups() -> list[MedicationGroup]:
    return [
        MedicationGroup(
            key="morning",
            label="Morning",
            meds=[
                MedicationItem(
                    dose="morning dose",
                    key="propranolol_morning",
                    label="Propranolol",
                    short="Pro",
                    total=1,
                ),
                MedicationItem(
                    dose="30mg XR",
                    key="adderall_xr",
                    label="Adderall XR",
                    short="XR",
                    total=1,
                ),
                MedicationItem(
                    dose="2 pills with food",
                    key="multivitamin",
                    label="Multivitamin",
                    short="MV",
                    total=2,
                ),
            ],
        ),
        MedicationGroup(
            key="afternoon",
            label="Afternoon",
            meds=[
                MedicationItem(
                    dose="20mg IR",
                    key="adderall_ir",
                    label="Adderall IR",
                    short="IR",
                    total=1,
                ),
                MedicationItem(
                    dose="3 pills",
                    key="omega_3",
                    label="Omega 3",
                    short="Ω3",
                    total=3,
                ),
            ],
        ),
        MedicationGroup(
            key="night",
            label="Night",
            meds=[
                MedicationItem(
                    dose="night dose",
                    key="propranolol_night",
                    label="Propranolol",
                    short="Pro",
                    total=1,
                ),
                MedicationItem(
                    dose="2 x 100mg",
                    key="magnesium",
                    label="Magnesium",
                    short="Mg",
                    total=2,
                ),
                MedicationItem(
                    dose="night / anxiety",
                    key="hydroxyzine",
                    label="Hydroxyzine",
                    short="Hyd",
                    prn=True,
                    total=0,
                ),
            ],
        ),
    ]
