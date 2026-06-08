import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var viewModel: AppViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                hero

                if let notice = viewModel.notice {
                    NoticeBanner(notice: notice)
                }

                medicationCard

                if viewModel.isLoading {
                    Panel { LoadingRows() }
                } else if viewModel.lastConnectionError != nil && viewModel.monthState == nil {
                    ConnectionHelpPanel(baseURL: viewModel.apiBaseURL) {
                        Task { await viewModel.refresh() }
                    }
                } else if viewModel.todayEntries.isEmpty {
                    emptyState
                } else {
                    entries
                }
            }
            .padding(18)
        }
        .background(Color(uiColor: .systemGroupedBackground).ignoresSafeArea())
        .navigationTitle("Today")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Task { await viewModel.refresh() }
                } label: {
                    Label("Refresh", systemImage: "arrow.clockwise")
                }
                .disabled(viewModel.isLoading)
            }
        }
        .refreshable {
            await viewModel.refresh()
        }
        .onChange(of: viewModel.selectedDate) {
            Task { await viewModel.refresh() }
        }
    }

    private var hero: some View {
        Panel {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("HabitOS")
                            .font(.caption.weight(.bold))
                            .textCase(.uppercase)
                            .tracking(1.2)
                            .foregroundStyle(.secondary)
                        Text(viewModel.selectedDate, format: .dateTime.weekday(.wide).month().day())
                            .font(.largeTitle.weight(.bold))
                            .foregroundStyle(.primary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer()
                    DatePicker("Date", selection: $viewModel.selectedDate, displayedComponents: .date)
                        .labelsHidden()
                }

                HStack(spacing: 12) {
                    StatPill(
                        title: "Habits",
                        value: "\(viewModel.completionSummary.done)/\(max(viewModel.completionSummary.total, 1))",
                        systemImage: "checklist.checked"
                    )
                    StatPill(
                        title: "Meds",
                        value: viewModel.selectedMedicationCounts.isEmpty ? "Open" : "Logged",
                        systemImage: "pills.fill"
                    )
                }
            }
        }
    }

    private var medicationCard: some View {
        NavigationLink {
            MedicationLogView()
        } label: {
            Panel {
                HStack(spacing: 14) {
                    Image(systemName: "pills.fill")
                        .font(.title2)
                        .foregroundStyle(.white)
                        .frame(width: 48, height: 48)
                        .background(Color.accentColor)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Update medication")
                            .font(.headline.weight(.bold))
                            .foregroundStyle(.primary)
                        Text(viewModel.medicationSummary)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.headline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var emptyState: some View {
        Panel {
            VStack(alignment: .leading, spacing: 10) {
                Text("No entries for this day")
                    .font(.title3.weight(.bold))
                Text("Sync tracker data or log medication to start filling the day. This app stays lightweight and writes back to HabitOS as the source of truth.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var entries: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Resolved habits")
                .font(.headline.weight(.bold))
                .padding(.horizontal, 4)
            ForEach(viewModel.todayEntries) { entry in
                HabitEntryRow(entry: entry)
            }
        }
    }
}

private struct StatPill: View {
    let title: String
    let value: String
    let systemImage: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: systemImage)
                .foregroundStyle(Color.accentColor)
            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                Text(value)
                    .font(.headline.monospacedDigit().weight(.bold))
                    .foregroundStyle(.primary)
            }
            Spacer(minLength: 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(Color(uiColor: .tertiarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

private struct HabitEntryRow: View {
    let entry: HabitEntry

    var body: some View {
        Panel {
            HStack(alignment: .top, spacing: 14) {
                statusMark
                VStack(alignment: .leading, spacing: 6) {
                    Text(entry.habitKey.replacingOccurrences(of: "_", with: " ").capitalized)
                        .font(.headline.weight(.bold))
                    Text(entry.summary.isEmpty ? entry.status.label : entry.summary)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    if !entry.explanation.isEmpty {
                        Text(entry.explanation)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: 0)
            }
        }
    }

    private var statusMark: some View {
        Image(systemName: entry.status == .checked || entry.status == .manual ? "checkmark" : entry.status == .missed ? "minus" : "circle.fill")
            .font(.headline.weight(.bold))
            .foregroundStyle(statusColor)
            .frame(width: 38, height: 38)
            .background(statusColor.opacity(0.12))
            .clipShape(Circle())
            .accessibilityLabel(entry.status.label)
    }

    private var statusColor: Color {
        switch entry.status {
        case .checked, .manual: HabitOSDesign.success
        case .partial, .warning: HabitOSDesign.warning
        case .missed: HabitOSDesign.danger
        }
    }
}
