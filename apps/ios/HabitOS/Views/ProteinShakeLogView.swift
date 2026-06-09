import SwiftUI

struct ProteinShakeLogView: View {
    @EnvironmentObject private var viewModel: AppViewModel
    @State private var count = 1

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

                        countCard

                        savePanel
                    }
                    .padding(12)
                }
                .navigationTitle("Protein Shake")
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
                        .disabled(viewModel.isLoading || viewModel.isSavingProteinShake)
                    }
                }
                .onAppear(perform: loadCountFromState)
                .onChange(of: viewModel.monthState) { loadCountFromState() }
                .onChange(of: viewModel.selectedDate) { loadCountFromState() }
                .onChange(of: viewModel.notice) { _, _ in
                    withAnimation(.easeOut(duration: 0.12)) {
                        proxy.scrollTo("top", anchor: .top)
                    }
                }
            }
        }
    }

    private func loadCountFromState() {
        count = viewModel.selectedProteinShakeCount
    }

    private var header: some View {
        PaperPanel {
            VStack(alignment: .leading, spacing: 14) {
                Text("Protein shake log")
                    .font(HabitOSFont.meta)
                    .foregroundStyle(Color.inkFaint)
                Text("Tap +/- to log shakes")
                    .font(HabitOSFont.h1)
                    .foregroundStyle(Color.ink)
                DatePicker("Date", selection: $viewModel.selectedDate, displayedComponents: .date)
                    .datePickerStyle(.compact)
                    .foregroundStyle(Color.ink)
                    .tint(Color.accent)
            }
        }
    }

    private var countCard: some View {
        PaperPanel {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Protein Shake")
                            .font(HabitOSFont.h3)
                            .foregroundStyle(Color.ink)
                        Text("How many shakes today?")
                            .font(HabitOSFont.data)
                            .foregroundStyle(Color.inkFaint)
                    }
                    Spacer()
                }

                HStack(spacing: 12) {
                    CountButton(systemImage: "minus", disabled: count == 0) {
                        Haptic.light()
                        count = max(0, count - 1)
                    }

                    Text("\(count)")
                        .font(.system(size: 42, weight: .black, design: .monospaced))
                        .frame(minWidth: 72)
                        .foregroundStyle(Color.ink)
                        .accessibilityLabel("Protein shake count \(count)")
                        .contentTransition(.numericText())

                    CountButton(systemImage: "plus", filled: true, disabled: count >= 20) {
                        Haptic.light()
                        count = min(20, count + 1)
                    }
                }
            }
        }
    }

    private var savePanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Toggle("Update habits after saving", isOn: $viewModel.recomputeAfterProteinShakeSave)
                .font(HabitOSFont.data)
                .foregroundStyle(Color.ink)
                .padding(.horizontal, 4)
            Button {
                Haptic.medium()
                Task { await viewModel.saveProteinShake(count: count) }
            } label: {
                if viewModel.isSavingProteinShake {
                    ProgressView()
                        .tint(.white)
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Save log")
                }
            }
            .buttonStyle(PrimaryButtonStyle())
            .disabled(viewModel.isSavingProteinShake)
        }
        .padding(.top, 4)
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
