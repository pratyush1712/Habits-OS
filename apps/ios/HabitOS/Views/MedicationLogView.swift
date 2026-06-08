import SwiftUI

struct MedicationLogView: View {
    @EnvironmentObject private var viewModel: AppViewModel
    @State private var counts: [String: Int] = [:]

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

                        ForEach(viewModel.medicationGroups) { group in
                            MedicationGroupCard(group: group, counts: $counts)
                        }

                        savePanel
                    }
                    .padding(18)
                }
                .navigationTitle("Medication")
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
                        .disabled(viewModel.isLoading || viewModel.isSavingMedication)
                    }
                }
                .onAppear(perform: loadCountsFromState)
                .onChange(of: viewModel.monthState) { loadCountsFromState() }
                .onChange(of: viewModel.selectedDate) { loadCountsFromState() }
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
                Text("Medication log")
                    .font(HabitOSFont.meta)
                    .foregroundStyle(Color.inkFaint)
                Text("Tap +/- to log doses")
                    .font(HabitOSFont.h1)
                    .foregroundStyle(Color.ink)
                DatePicker("Date", selection: $viewModel.selectedDate, displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .foregroundStyle(Color.ink)
                    .tint(Color.accent)
                Text(viewModel.medicationSummary)
                    .font(HabitOSFont.data)
                    .foregroundStyle(Color.inkFaint)
            }
        }
    }

    private var savePanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle("Update habits after saving", isOn: $viewModel.recomputeAfterMedicationSave)
                .font(HabitOSFont.data)
                .padding(.horizontal, 4)
            Button {
                Haptic.medium()
                Task { await viewModel.saveMedication(counts: counts) }
            } label: {
                if viewModel.isSavingMedication {
                    ProgressView()
                        .tint(.white)
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Save log")
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
                .font(HabitOSFont.h3)
                .foregroundStyle(Color.ink)
                .padding(.horizontal, 4)

            PaperPanel {
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
                        .font(HabitOSFont.h3)
                        .foregroundStyle(Color.ink)
                    Text(med.prn ? "As needed · \(med.dose)" : med.dose)
                        .font(HabitOSFont.data)
                        .foregroundStyle(Color.inkFaint)
                }
                Spacer()
                Text(med.prn ? "PRN" : "Goal \(med.total)")
                    .font(HabitOSFont.meta)
                    .foregroundStyle(Color.ink)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.paperDeep)
                    .overlay(Rectangle().stroke(Color.rule, lineWidth: 2))
            }

            HStack(spacing: 12) {
                CountButton(systemImage: "minus", disabled: value == 0) {
                    Haptic.light()
                    value = max(0, value - 1)
                }

                Text("\(value)")
                    .font(.system(size: 42, weight: .black, design: .monospaced))
                    .frame(minWidth: 72)
                    .foregroundStyle(Color.ink)
                    .accessibilityLabel("\(med.label) taken count \(value)")
                    .contentTransition(.numericText())

                CountButton(systemImage: "plus", filled: true) {
                    Haptic.light()
                    value += 1
                }

                if !med.prn {
                    Button("Fill") {
                        Haptic.medium()
                        value = med.total
                    }
                    .font(HabitOSFont.body)
                    .buttonStyle(SecondaryButtonStyle())
                }
            }
        }
        .padding(14)
        .background(Color.paper)
        .overlay(Rectangle().stroke(Color.ruleSoft, lineWidth: 2))
    }
}

private struct CountButton: View {
    let systemImage: String
    var filled = false
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(HabitOSFont.body)
                .frame(width: 52, height: 52)
        }
        .buttonStyle(CountButtonStyle(filled: filled))
        .disabled(disabled)
    }
}
