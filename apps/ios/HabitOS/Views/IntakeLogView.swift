import SwiftUI

struct IntakeLogView: View {
    @EnvironmentObject private var viewModel: AppViewModel
    @State private var advancedProduct: IntakeProductPreset?

    var body: some View {
        ZStack {
            GridBackground()

            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 18) {
                        header
                            .id("top")

                        if let notice = viewModel.notice {
                            NoticeBanner(notice: notice) {
                                viewModel.dismissNotice()
                            }
                        }

                        bundleList

                        saveOptions
                    }
                    .padding(12)
                }
                .navigationTitle("Intake")
                .refreshable {
                    await viewModel.refresh()
                }
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            Haptic.medium()
                            Task { await viewModel.refresh() }
                        } label: {
                            Label("Refresh", systemImage: "arrow.clockwise")
                        }
                        .disabled(viewModel.isLoading || viewModel.isSavingIntake)
                    }
                }
                .sheet(item: $advancedProduct) { product in
                    IngredientPickerSheet(product: product) { selectedItems in
                        advancedProduct = nil
                        Haptic.medium()
                        Task { await viewModel.saveIntake(items: selectedItems) }
                    }
                    .presentationDetents([.medium, .large])
                    .presentationDragIndicator(.visible)
                }
                .onChange(of: viewModel.notice) { _, _ in
                    withAnimation(.easeOut(duration: 0.12)) {
                        proxy.scrollTo("top", anchor: .top)
                    }
                }
            }
        }
    }

    private var header: some View {
        PaperPanel {
            VStack(alignment: .leading, spacing: 14) {
                Text("Intake log")
                    .font(HabitOSFont.meta)
                    .foregroundStyle(Color.inkFaint)
                Text("Log the product you took")
                    .font(HabitOSFont.h1)
                    .foregroundStyle(Color.ink)
                DatePicker("Date", selection: $viewModel.selectedDate, displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .foregroundStyle(Color.ink)
                    .tint(Color.accent)
                Text(viewModel.selectedIntakeSummary)
                    .font(HabitOSFont.data)
                    .foregroundStyle(Color.inkFaint)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var bundleList: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Usual products")
                .font(HabitOSFont.h3)
                .foregroundStyle(Color.ink)
                .padding(.horizontal, 4)

            ForEach(IntakeCatalog.products) { product in
                ProductBundleCard(
                    product: product,
                    isSaving: viewModel.isSavingIntake,
                    logBundle: {
                        Haptic.medium()
                        Task { await viewModel.saveIntake(items: product.items) }
                    },
                    customize: {
                        Haptic.light()
                        advancedProduct = product
                    }
                )
            }
        }
    }

    private var saveOptions: some View {
        Toggle("Update habits after saving", isOn: $viewModel.recomputeAfterIntakeSave)
            .font(HabitOSFont.data)
            .foregroundStyle(Color.ink)
            .padding(.horizontal, 4)
            .padding(.top, 4)
    }
}

private struct ProductBundleCard: View {
    let product: IntakeProductPreset
    let isSaving: Bool
    let logBundle: () -> Void
    let customize: () -> Void

    var body: some View {
        PaperPanel {
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: product.systemImage)
                        .font(HabitOSFont.h3)
                        .foregroundStyle(.white)
                        .frame(width: 48, height: 48)
                        .background(Color.rule)

                    VStack(alignment: .leading, spacing: 5) {
                        Text(product.brandLabel)
                            .font(HabitOSFont.meta)
                            .foregroundStyle(Color.inkFaint)
                        Text(product.productLabel)
                            .font(HabitOSFont.h3)
                            .foregroundStyle(Color.ink)
                        Text(product.summary)
                            .font(HabitOSFont.data)
                            .foregroundStyle(Color.inkMid)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                Button {
                    logBundle()
                } label: {
                    if isSaving {
                        ProgressView()
                            .tint(.white)
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("Log full product")
                    }
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(isSaving)

                Button("Choose specific ingredients", action: customize)
                    .buttonStyle(SecondaryButtonStyle())
                    .disabled(isSaving)
            }
        }
    }
}

private struct IngredientPickerSheet: View {
    let product: IntakeProductPreset
    let save: ([IntakeItemInput]) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var selectedKeys: Set<String>

    init(product: IntakeProductPreset, save: @escaping ([IntakeItemInput]) -> Void) {
        self.product = product
        self.save = save
        _selectedKeys = State(initialValue: Set(product.items.map(\.key)))
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(product.items) { item in
                        Button {
                            if selectedKeys.contains(item.key) {
                                selectedKeys.remove(item.key)
                            } else {
                                selectedKeys.insert(item.key)
                            }
                            Haptic.light()
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: selectedKeys.contains(item.key) ? "checkmark.square.fill" : "square")
                                    .foregroundStyle(selectedKeys.contains(item.key) ? Color.accentHot : Color.inkFaint)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(item.ingredientLabel)
                                        .font(HabitOSFont.body)
                                        .foregroundStyle(Color.ink)
                                    Text(item.category.replacingOccurrences(of: "_", with: " "))
                                        .font(HabitOSFont.meta)
                                        .foregroundStyle(Color.inkFaint)
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(.vertical, 6)
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .listRowBackground(Color.white)
                    }
                } header: {
                    Text("Only use this when you skipped or mixed components.")
                        .font(HabitOSFont.meta)
                        .foregroundStyle(Color.inkFaint)
                }
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(Color.paper)
            .navigationTitle(product.productLabel)
            .toolbarBackground(Color.paper, for: .navigationBar)
            .toolbarBackground(.visible, for: .navigationBar)
            .tint(Color.accent)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        let selected = product.items.filter { selectedKeys.contains($0.key) }
                        save(selected)
                    }
                    .disabled(selectedKeys.isEmpty)
                }
            }
        }
    }
}

private struct IntakeProductPreset: Identifiable, Hashable {
    let brandKey: String
    let brandLabel: String
    let productKey: String
    let productLabel: String
    let timeOfDay: String
    let systemImage: String
    let summary: String
    let ingredients: [IntakeIngredientPreset]

    var id: String { productKey }

    var items: [IntakeItemInput] {
        ingredients.map { ingredient in
            IntakeItemInput(
                key: "\(productKey)_\(ingredient.ingredientKey)",
                label: "\(productLabel) — \(ingredient.ingredientLabel)",
                brandKey: brandKey,
                brandLabel: brandLabel,
                productKey: productKey,
                productLabel: productLabel,
                ingredientKey: ingredient.ingredientKey,
                ingredientLabel: ingredient.ingredientLabel,
                category: ingredient.category,
                amount: ingredient.amount,
                unit: ingredient.unit,
                caffeineMg: ingredient.caffeineMg,
                timeOfDay: timeOfDay,
                notes: ingredient.notes ?? "Logged from HabitOS mobile intake preset."
            )
        }
    }
}

private struct IntakeIngredientPreset: Hashable {
    let ingredientKey: String
    let ingredientLabel: String
    let category: String
    let amount: Double?
    let unit: String
    let caffeineMg: Int?
    let notes: String?

    init(
        _ ingredientKey: String,
        _ ingredientLabel: String,
        category: String,
        amount: Double? = nil,
        unit: String = "",
        caffeineMg: Int? = nil,
        notes: String? = nil
    ) {
        self.ingredientKey = ingredientKey
        self.ingredientLabel = ingredientLabel
        self.category = category
        self.amount = amount
        self.unit = unit
        self.caffeineMg = caffeineMg
        self.notes = notes
    }
}

private enum IntakeCatalog {
    static let products: [IntakeProductPreset] = [
        IntakeProductPreset(
            brandKey: "everyday_dose",
            brandLabel: "Everyday Dose",
            productKey: "everyday_dose_coffee_plus",
            productLabel: "Everyday Dose Coffee+",
            timeOfDay: "morning",
            systemImage: "cup.and.saucer.fill",
            summary: "Coffee+, collagen, mushrooms, L-theanine, and amino acids.",
            ingredients: [
                IntakeIngredientPreset("caffeine", "Caffeine", category: "stimulant", amount: 45, unit: "mg", caffeineMg: 45),
                IntakeIngredientPreset("coffee_extract", "Coffee Extract", category: "coffee"),
                IntakeIngredientPreset("hydrolyzed_bovine_collagen_peptides", "Hydrolyzed Bovine Collagen Peptides", category: "collagen"),
                IntakeIngredientPreset("l_theanine", "L-Theanine", category: "amino_acid"),
                IntakeIngredientPreset("chaga", "Chaga Fruiting Body Extract", category: "mushroom"),
                IntakeIngredientPreset("lions_mane", "Lion's Mane Fruiting Body Extract", category: "mushroom"),
                IntakeIngredientPreset("glycine", "Glycine", category: "amino_acid", amount: 1044, unit: "mg"),
                IntakeIngredientPreset("l_proline", "L-Proline", category: "amino_acid", amount: 629, unit: "mg"),
                IntakeIngredientPreset("l_hydroxyproline", "L-Hydroxyproline", category: "amino_acid", amount: 520, unit: "mg"),
                IntakeIngredientPreset("l_glutamic_acid", "L-Glutamic Acid", category: "amino_acid", amount: 473, unit: "mg"),
                IntakeIngredientPreset("l_alanine", "L-Alanine", category: "amino_acid", amount: 418, unit: "mg"),
                IntakeIngredientPreset("l_arginine", "L-Arginine", category: "amino_acid", amount: 383, unit: "mg"),
                IntakeIngredientPreset("l_aspartic_acid", "L-Aspartic Acid", category: "amino_acid", amount: 265, unit: "mg"),
                IntakeIngredientPreset("l_lysine", "L-Lysine", category: "amino_acid", amount: 170, unit: "mg"),
                IntakeIngredientPreset("l_serine", "L-Serine", category: "amino_acid", amount: 156, unit: "mg"),
                IntakeIngredientPreset("l_leucine", "L-Leucine", category: "amino_acid", amount: 137, unit: "mg"),
            ]
        ),
        IntakeProductPreset(
            brandKey: "cuppa",
            brandLabel: "Cuppa",
            productKey: "cuppa_healthy_coffee",
            productLabel: "Cuppa Healthy Coffee",
            timeOfDay: "morning",
            systemImage: "leaf.fill",
            summary: "Coffee with KSM-66 ashwagandha, lion's mane, cordyceps, L-theanine, MCT, and fiber.",
            ingredients: [
                IntakeIngredientPreset("caffeine", "Caffeine", category: "stimulant", amount: 70, unit: "mg", caffeineMg: 70),
                IntakeIngredientPreset("arabica_coffee", "100% Arabica Coffee", category: "coffee"),
                IntakeIngredientPreset("ksm66_ashwagandha", "KSM-66 Ashwagandha Root Extract", category: "adaptogen", amount: 250, unit: "mg"),
                IntakeIngredientPreset("lions_mane", "Lion's Mane Fruiting Body Extract", category: "mushroom", amount: 1000, unit: "mg", notes: "Equivalent mushroom amount; concentrated extract."),
                IntakeIngredientPreset("cordyceps", "Cordyceps Fruiting Body Extract", category: "mushroom", amount: 1000, unit: "mg", notes: "Equivalent mushroom amount; concentrated extract."),
                IntakeIngredientPreset("l_theanine", "L-Theanine", category: "amino_acid", amount: 100, unit: "mg"),
                IntakeIngredientPreset("mct", "Medium Chain Triglycerides", category: "fat", amount: 500, unit: "mg"),
                IntakeIngredientPreset("acacia_fiber", "Acacia Fiber", category: "fiber", amount: 500, unit: "mg"),
                IntakeIngredientPreset("natural_vanilla_flavor", "Natural Vanilla Flavor", category: "flavor"),
            ]
        )
    ]
}
