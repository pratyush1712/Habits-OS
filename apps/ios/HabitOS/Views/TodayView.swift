import SwiftUI

struct TodayView: View {
    @EnvironmentObject private var viewModel: AppViewModel

    var body: some View {
        ZStack {
            GridBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    hero

                    if let notice = viewModel.notice {
                        NoticeBanner(notice: notice) {
                            viewModel.dismissNotice()
                        }
                    }

                    medicationCard

                    if viewModel.isLoading {
                        PaperPanel { LoadingRows() }
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
        }
        .navigationTitle("Today")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    Haptic.medium()
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
        PaperPanel {
            VStack(alignment: .leading, spacing: 16) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("HabitOS")
                            .font(HabitOSFont.meta)
                            .foregroundStyle(Color.inkFaint)
                        Text(viewModel.selectedDate, format: .dateTime.weekday(.wide).month().day())
                            .font(HabitOSFont.h1)
                            .foregroundStyle(Color.ink)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer()
                    DatePicker("Date", selection: $viewModel.selectedDate, displayedComponents: .date)
                        .labelsHidden()
                        .foregroundStyle(Color.ink)
                        .tint(Color.accent)
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
            PaperPanel {
                HStack(spacing: 14) {
                    Image(systemName: "pills.fill")
                        .font(HabitOSFont.h3)
                        .foregroundStyle(.white)
                        .frame(width: 48, height: 48)
                        .background(Color.rule)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Log medication")
                            .font(HabitOSFont.h3)
                            .foregroundStyle(Color.ink)
                        Text(viewModel.medicationSummary)
                            .font(HabitOSFont.data)
                            .foregroundStyle(Color.inkFaint)
                            .lineLimit(1)
                    }

                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(HabitOSFont.body)
                        .foregroundStyle(Color.inkFaint)
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var emptyState: some View {
        PaperPanel {
            VStack(alignment: .leading, spacing: 10) {
                Text("Nothing logged yet")
                    .font(HabitOSFont.h3)
                    .foregroundStyle(Color.ink)
                Text("Pull down to refresh tracker data, or tap Log medication to record doses for this day.")
                    .font(HabitOSFont.body)
                    .foregroundStyle(Color.inkMid)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var entries: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Resolved habits")
                .font(HabitOSFont.h3)
                .foregroundStyle(Color.ink)
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
                .foregroundStyle(Color.accent)
                .font(HabitOSFont.data)
            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(HabitOSFont.meta)
                    .foregroundStyle(Color.inkFaint)
                Text(value)
                    .font(HabitOSFont.data)
                    .foregroundStyle(Color.ink)
            }
            Spacer(minLength: 0)
        }
        .padding(12)
        .frame(maxWidth: .infinity)
        .background(Color.paperDeep)
        .overlay(Rectangle().stroke(Color.rule, lineWidth: 2))
    }
}

private struct HabitEntryRow: View {
    let entry: HabitEntry

    var body: some View {
        PaperPanel {
            HStack(alignment: .top, spacing: 14) {
                statusMark
                VStack(alignment: .leading, spacing: 6) {
                    Text(entry.habitKey.replacingOccurrences(of: "_", with: " ").capitalized)
                        .font(HabitOSFont.h3)
                        .foregroundStyle(Color.ink)
                    Text(entry.summary.isEmpty ? entry.status.label : entry.summary)
                        .font(HabitOSFont.data)
                        .foregroundStyle(Color.inkMid)
                        .fixedSize(horizontal: false, vertical: true)
                    if !entry.explanation.isEmpty {
                        Text(entry.explanation)
                            .font(HabitOSFont.meta)
                            .foregroundStyle(Color.inkFaint)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                Spacer(minLength: 0)
            }
        }
    }

    private var statusMark: some View {
        Image(systemName: entry.status == .checked || entry.status == .manual ? "checkmark" : entry.status == .missed ? "minus" : "circle.fill")
            .font(HabitOSFont.body)
            .foregroundStyle(statusColor)
            .frame(width: 38, height: 38)
            .background(statusColor.opacity(0.15))
            .overlay(Rectangle().stroke(statusColor, lineWidth: 2))
            .accessibilityLabel(entry.status.label)
    }

    private var statusColor: Color {
        switch entry.status {
        case .checked, .manual: Color.accentHot
        case .partial, .warning: Color.redPanel
        case .missed: Color.anomaly
        }
    }
}
