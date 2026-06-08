import SwiftUI

struct MedicationLogView: View {
    @EnvironmentObject private var viewModel: AppViewModel
    @State private var counts: [String: Int] = [:]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                        .id("top")

                    if let notice = viewModel.notice {
                        NoticeBanner(notice: notice)
                    }

                    ForEach(viewModel.medicationGroups) { group in
                        MedicationGroupCard(group: group, counts: $counts)
                    }

                    savePanel
                }
                .padding(18)
            }
            .background(Color(uiColor: .systemGroupedBackground).ignoresSafeArea())
            .navigationTitle("Medication")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Reload") {
                        Task { await viewModel.refresh() }
                    }
                    .disabled(viewModel.isLoading || viewModel.isSavingMedication)
                }
            }
            .onAppear(perform: loadCountsFromState)
            .onChange(of: viewModel.monthState) { loadCountsFromState() }
            .onChange(of: viewModel.selectedDate) { loadCountsFromState() }
            .onChange(of: viewModel.notice) { _, _ in
                withAnimation(.smooth) {
                    proxy.scrollTo("top", anchor: .top)
                }
            }
        }
    }

    private var header: some View {
        Panel {
            VStack(alignment: .leading, spacing: 14) {
                Text("Medication log")
                    .font(.caption.weight(.bold))
                    .textCase(.uppercase)
                    .tracking(1.2)
                    .foregroundStyle(.secondary)
                Text("Tap counts. Save once.")
                    .font(.largeTitle.weight(.bold))
                    .foregroundStyle(.primary)
                DatePicker("Date", selection: $viewModel.selectedDate, displayedComponents: .date)
                    .datePickerStyle(.compact)
                Text(viewModel.medicationSummary)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var savePanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle("Recompute month after save", isOn: $viewModel.recomputeAfterMedicationSave)
                .font(.headline)
                .padding(.horizontal, 4)
            Button {
                Task { await viewModel.saveMedication(counts: counts) }
            } label: {
                if viewModel.isSavingMedication {
                    ProgressView()
                        .tint(.white)
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Save medication log")
                }
            }
            .buttonStyle(PrimaryButtonStyle())
            .disabled(viewModel.isSavingMedication)
        }
        .padding(.top, 4)
    }

    private func loadCountsFromState() {
        let existing = viewModel.selectedMedicationCounts
        var next: [String: Int] = [:]
        for group in viewModel.medicationGroups {
            for med in group.meds {
                next[med.key] = existing[med.key] ?? counts[med.key] ?? 0
            }
        }
        counts = next
    }
}

private struct MedicationGroupCard: View {
    let group: MedicationGroup
    @Binding var counts: [String: Int]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(group.label)
                .font(.headline.weight(.bold))
                .foregroundStyle(.secondary)
                .padding(.horizontal, 4)

            Panel {
                VStack(spacing: 12) {
                    ForEach(group.meds) { med in
                        MedicationDoseRow(med: med, value: binding(for: med))
                    }
                }
            }
        }
    }

    private func binding(for med: MedicationItem) -> Binding<Int> {
        Binding(
            get: { counts[med.key] ?? 0 },
            set: { counts[med.key] = max(0, $0) }
        )
    }
}

private struct MedicationDoseRow: View {
    let med: MedicationItem
    @Binding var value: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(med.label)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.primary)
                    Text(med.prn ? "As needed · \(med.dose)" : med.dose)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text(med.prn ? "PRN" : "Goal \(med.total)")
                    .font(.caption.monospacedDigit().weight(.bold))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.accentColor.opacity(0.12))
                    .clipShape(Capsule())
            }

            HStack(spacing: 12) {
                CountButton(systemImage: "minus", disabled: value == 0) {
                    value = max(0, value - 1)
                }

                Text("\(value)")
                    .font(.system(size: 42, weight: .black, design: .rounded).monospacedDigit())
                    .frame(minWidth: 72)
                    .foregroundStyle(.primary)
                    .accessibilityLabel("\(med.label) taken count \(value)")

                CountButton(systemImage: "plus", filled: true) {
                    value += 1
                }

                if !med.prn {
                    Button("Full") {
                        value = med.total
                    }
                    .font(.headline.weight(.bold))
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding(14)
        .background(Color(uiColor: .systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(Color.primary.opacity(0.08), lineWidth: 1)
        )
    }
}

private struct CountButton: View {
    let systemImage: String
    var filled = false
    var disabled = false
    let action: () -> Void

    var body: some View {
        if filled {
            Button(action: action) {
                Image(systemName: systemImage)
                    .font(.title3.weight(.bold))
                    .frame(width: 52, height: 52)
            }
            .buttonStyle(.borderedProminent)
            .tint(.accentColor)
            .disabled(disabled)
        } else {
            Button(action: action) {
                Image(systemName: systemImage)
                    .font(.title3.weight(.bold))
                    .frame(width: 52, height: 52)
            }
            .buttonStyle(.bordered)
            .tint(.accentColor)
            .disabled(disabled)
        }
    }
}
