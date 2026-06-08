export type MedicationPlanItem = {
  dose: string;
  key: string;
  label: string;
  notes?: string;
  prn?: boolean;
  total: number;
};

export type MedicationPlanGroup = {
  key: string;
  label: string;
  meds: MedicationPlanItem[];
};

export const MEDICATION_PLAN: MedicationPlanGroup[] = [
  {
    key: "morning",
    label: "Morning",
    meds: [
      {
        dose: "morning dose",
        key: "propranolol_morning",
        label: "Propranolol",
        total: 1,
      },
      {
        dose: "30mg XR",
        key: "adderall_xr",
        label: "Adderall XR",
        notes: "Once in the morning.",
        total: 1,
      },
      {
        dose: "2 pills with food",
        key: "multivitamin",
        label: "Multivitamin",
        notes: "Keep roughly one hour away from Adderall.",
        total: 2,
      },
    ],
  },
  {
    key: "afternoon",
    label: "Afternoon",
    meds: [
      {
        dose: "20mg IR",
        key: "adderall_ir",
        label: "Adderall IR",
        notes: "Once in the afternoon.",
        total: 1,
      },
      {
        dose: "3 pills",
        key: "omega_3",
        label: "Omega 3",
        notes: "Fish oil target: 1300mg EPA / 860mg DHA.",
        total: 3,
      },
    ],
  },
  {
    key: "night",
    label: "Night",
    meds: [
      {
        dose: "night dose",
        key: "propranolol_night",
        label: "Propranolol",
        total: 1,
      },
      {
        dose: "2 x 100mg",
        key: "magnesium",
        label: "Magnesium",
        notes: "Before sleeping.",
        total: 2,
      },
      {
        dose: "night / anxiety",
        key: "hydroxyzine",
        label: "Hydroxyzine",
        notes: "As-needed logging only; untouched is not counted as missed.",
        prn: true,
        total: 0,
      },
    ],
  },
];

export const MEDICATION_ITEMS = MEDICATION_PLAN.flatMap((group) => group.meds);
