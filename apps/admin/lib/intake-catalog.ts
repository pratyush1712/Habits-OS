import type { IntakeCategory, IntakeTimeOfDay } from "./api-client";

export type IntakeIngredientPreset = {
  amount?: number;
  caffeineMg?: number;
  category: IntakeCategory;
  ingredientKey: string;
  ingredientLabel: string;
  notes?: string;
  unit?: string;
};

export type IntakeProductPreset = {
  brandKey: string;
  brandLabel: string;
  defaultAmount: number;
  defaultTimeOfDay: IntakeTimeOfDay;
  defaultUnit: string;
  evidence: string;
  ingredients: IntakeIngredientPreset[];
  productKey: string;
  productLabel: string;
};

export function intakeItemKey(productKey: string, ingredientKey: string): string {
  return `${productKey}_${ingredientKey}`;
}

export const INTAKE_PRODUCTS: IntakeProductPreset[] = [
  {
    brandKey: "everyday_dose",
    brandLabel: "Everyday Dose",
    defaultAmount: 1,
    defaultTimeOfDay: "morning",
    defaultUnit: "serving",
    evidence: "Official Everyday Dose Coffee+ label/product pages; amino-acid panel where visible.",
    productKey: "everyday_dose_coffee_plus",
    productLabel: "Everyday Dose Coffee+",
    ingredients: [
      { amount: 45, caffeineMg: 45, category: "stimulant", ingredientKey: "caffeine", ingredientLabel: "Caffeine", unit: "mg" },
      { category: "coffee", ingredientKey: "coffee_extract", ingredientLabel: "Coffee Extract" },
      { category: "collagen", ingredientKey: "hydrolyzed_bovine_collagen_peptides", ingredientLabel: "Hydrolyzed Bovine Collagen Peptides" },
      { category: "amino_acid", ingredientKey: "l_theanine", ingredientLabel: "L-Theanine" },
      { category: "mushroom", ingredientKey: "chaga", ingredientLabel: "Chaga Fruiting Body Extract" },
      { category: "mushroom", ingredientKey: "lions_mane", ingredientLabel: "Lion's Mane Fruiting Body Extract" },
      { amount: 1044, category: "amino_acid", ingredientKey: "glycine", ingredientLabel: "Glycine", unit: "mg" },
      { amount: 629, category: "amino_acid", ingredientKey: "l_proline", ingredientLabel: "L-Proline", unit: "mg" },
      { amount: 520, category: "amino_acid", ingredientKey: "l_hydroxyproline", ingredientLabel: "L-Hydroxyproline", unit: "mg" },
      { amount: 473, category: "amino_acid", ingredientKey: "l_glutamic_acid", ingredientLabel: "L-Glutamic Acid", unit: "mg" },
      { amount: 418, category: "amino_acid", ingredientKey: "l_alanine", ingredientLabel: "L-Alanine", unit: "mg" },
      { amount: 383, category: "amino_acid", ingredientKey: "l_arginine", ingredientLabel: "L-Arginine", unit: "mg" },
      { amount: 265, category: "amino_acid", ingredientKey: "l_aspartic_acid", ingredientLabel: "L-Aspartic Acid", unit: "mg" },
      { amount: 170, category: "amino_acid", ingredientKey: "l_lysine", ingredientLabel: "L-Lysine", unit: "mg" },
      { amount: 156, category: "amino_acid", ingredientKey: "l_serine", ingredientLabel: "L-Serine", unit: "mg" },
      { amount: 137, category: "amino_acid", ingredientKey: "l_leucine", ingredientLabel: "L-Leucine", unit: "mg" },
    ],
  },
  {
    brandKey: "everyday_dose",
    brandLabel: "Everyday Dose",
    defaultAmount: 1,
    defaultTimeOfDay: "morning",
    defaultUnit: "serving",
    evidence: "Prompt-visible Vanilla Creamer+ label; amounts visible for amino-acid stack.",
    productKey: "everyday_dose_vanilla_creamer_plus",
    productLabel: "Everyday Dose Vanilla Creamer+",
    ingredients: [
      { category: "dairy", ingredientKey: "organic_a2_milk", ingredientLabel: "Organic A2 Milk" },
      { category: "sweetener", ingredientKey: "organic_cane_sugar", ingredientLabel: "Organic Cane Sugar" },
      { category: "collagen", ingredientKey: "hydrolyzed_collagen_peptides", ingredientLabel: "Hydrolyzed Collagen Peptides" },
      { category: "flavor", ingredientKey: "natural_flavors", ingredientLabel: "Natural Flavors" },
      { category: "flavor", ingredientKey: "banana_powder", ingredientLabel: "Banana Powder" },
      { category: "mineral", ingredientKey: "sea_salt", ingredientLabel: "Sea Salt" },
      { category: "probiotic", ingredientKey: "de111_probiotic", ingredientLabel: "DE111 Probiotic" },
      { amount: 548, category: "amino_acid", ingredientKey: "glycine", ingredientLabel: "Glycine", unit: "mg" },
      { amount: 330, category: "amino_acid", ingredientKey: "l_proline", ingredientLabel: "L-Proline", unit: "mg" },
      { amount: 273, category: "amino_acid", ingredientKey: "l_hydroxyproline", ingredientLabel: "L-Hydroxyproline", unit: "mg" },
      { amount: 248, category: "amino_acid", ingredientKey: "l_glutamic_acid", ingredientLabel: "L-Glutamic Acid", unit: "mg" },
      { amount: 219, category: "amino_acid", ingredientKey: "l_alanine", ingredientLabel: "L-Alanine", unit: "mg" },
      { amount: 201, category: "amino_acid", ingredientKey: "l_arginine", ingredientLabel: "L-Arginine", unit: "mg" },
      { amount: 139, category: "amino_acid", ingredientKey: "l_aspartic_acid", ingredientLabel: "L-Aspartic Acid", unit: "mg" },
      { amount: 89, category: "amino_acid", ingredientKey: "l_lysine", ingredientLabel: "L-Lysine", unit: "mg" },
      { amount: 82, category: "amino_acid", ingredientKey: "l_serine", ingredientLabel: "L-Serine", unit: "mg" },
    ],
  },
  {
    brandKey: "cuppa",
    brandLabel: "Cuppa",
    defaultAmount: 1,
    defaultTimeOfDay: "morning",
    defaultUnit: "cup",
    evidence: "Official Cuppa product/FAQ pages and prompt-visible label.",
    productKey: "cuppa_healthy_coffee",
    productLabel: "Cuppa Healthy Coffee",
    ingredients: [
      { amount: 70, caffeineMg: 70, category: "stimulant", ingredientKey: "caffeine", ingredientLabel: "Caffeine", unit: "mg" },
      { category: "coffee", ingredientKey: "arabica_coffee", ingredientLabel: "100% Arabica Coffee" },
      { amount: 250, category: "adaptogen", ingredientKey: "ksm66_ashwagandha", ingredientLabel: "KSM-66 Ashwagandha Root Extract", unit: "mg" },
      { amount: 1000, category: "mushroom", ingredientKey: "lions_mane", ingredientLabel: "Lion's Mane Fruiting Body Extract", notes: "Equivalent mushroom amount; concentrated extract.", unit: "mg" },
      { amount: 1000, category: "mushroom", ingredientKey: "cordyceps", ingredientLabel: "Cordyceps Fruiting Body Extract", notes: "Equivalent mushroom amount; concentrated extract.", unit: "mg" },
      { amount: 100, category: "amino_acid", ingredientKey: "l_theanine", ingredientLabel: "L-Theanine", unit: "mg" },
      { amount: 500, category: "fat", ingredientKey: "mct", ingredientLabel: "Medium Chain Triglycerides", unit: "mg" },
      { amount: 500, category: "fiber", ingredientKey: "acacia_fiber", ingredientLabel: "Acacia Fiber", unit: "mg" },
      { category: "flavor", ingredientKey: "natural_vanilla_flavor", ingredientLabel: "Natural Vanilla Flavor" },
    ],
  },
  {
    brandKey: "ryze",
    brandLabel: "RYZE",
    defaultAmount: 1,
    defaultTimeOfDay: "night",
    defaultUnit: "cup",
    evidence: "Official RYZE Hot Cocoa page; exact sleep blend amounts from prompt-visible label/credible label review.",
    productKey: "ryze_mushroom_hot_cocoa",
    productLabel: "RYZE Mushroom Hot Cocoa",
    ingredients: [
      { category: "base", ingredientKey: "coconut_milk_powder", ingredientLabel: "Coconut Milk Powder" },
      { category: "base", ingredientKey: "coconut_water_powder", ingredientLabel: "Coconut Water Powder" },
      { category: "cacao", ingredientKey: "organic_cacao_powder", ingredientLabel: "Organic Cacao Powder" },
      { category: "fiber", ingredientKey: "chicory_root", ingredientLabel: "Chicory Root" },
      { amount: 1000, category: "amino_acid", ingredientKey: "glycine", ingredientLabel: "Glycine", unit: "mg" },
      { amount: 300, category: "mushroom", ingredientKey: "reishi", ingredientLabel: "Organic Reishi Extract", unit: "mg" },
      { amount: 200, category: "amino_acid", ingredientKey: "l_theanine", ingredientLabel: "L-Theanine", unit: "mg" },
      { amount: 15, category: "mineral", ingredientKey: "zinc_citrate", ingredientLabel: "Zinc (Zinc Citrate)", unit: "mg" },
      { amount: 3, category: "hormone", ingredientKey: "melatonin", ingredientLabel: "Melatonin", unit: "mg" },
    ],
  },
];
