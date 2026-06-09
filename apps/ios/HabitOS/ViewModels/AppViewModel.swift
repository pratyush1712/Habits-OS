import Foundation
import SwiftUI

@MainActor
final class AppViewModel: ObservableObject {
    @AppStorage("apiBaseURL") var apiBaseURL = "https://habits.pratyushsudhakar.com/api/mobile"
    @AppStorage("habitOSTimezone") var timezoneIdentifier = TimeZone.current.identifier
    @AppStorage("mobileAPIKey") var mobileAPIKey = ""
    @AppStorage("recomputeAfterMedicationSave") var recomputeAfterMedicationSave = true
    @AppStorage("recomputeAfterProteinShakeSave") var recomputeAfterProteinShakeSave = true

    @Published private(set) var monthState: MonthHabitState?
    @Published private(set) var isLoading = false
    @Published private(set) var isSavingMedication = false
    @Published private(set) var isSavingProteinShake = false
    @Published var selectedDate = Date() {
        didSet {
            // monthState caches a single month, so per-date lookups (habit
            // entries, medication doses, protein shake counts) only resolve
            // within it. Refetch when the selection crosses into another month;
            // same-month changes are served from the cache.
            guard monthState?.month != selectedMonth else { return }
            Task { await refresh() }
        }
    }
    @Published var notice: AppNotice?
    @Published private(set) var lastConnectionError: String?

    var selectedDateOnly: DateOnly {
        DateOnly(DateOnly.format(selectedDate, timeZone: selectedTimeZone))
    }

    var selectedMonth: String {
        String(selectedDateOnly.value.prefix(7))
    }

    var selectedTimeZone: TimeZone {
        TimeZone(identifier: timezoneIdentifier) ?? .current
    }

    var medicationGroups: [MedicationGroup] {
        let groups = monthState?.medicationGroups ?? []
        return groups.isEmpty ? MedicationGroup.fallbackPlan : groups
    }

    var todayEntries: [HabitEntry] {
        guard let monthState else { return [] }
        return monthState.entries
            .filter { $0.date == selectedDateOnly }
            .sorted { $0.habitKey < $1.habitKey }
    }

    var completionSummary: (done: Int, total: Int) {
        let actionable = todayEntries.filter { $0.status != .warning }
        let done = actionable.filter { $0.status == .checked || $0.status == .manual || $0.status == .partial }.count
        return (done, actionable.count)
    }

    var medicationSummary: String {
        let counts = selectedMedicationCounts
        let scheduled = medicationGroups.flatMap(\.meds).filter { !$0.prn }

        if scheduled.isEmpty {
            return "No scheduled medication plan loaded."
        }

        let taken = scheduled.reduce(0) { partial, med in
            partial + min(counts[med.key] ?? 0, med.total)
        }
        let total = scheduled.reduce(0) { $0 + $1.total }

        return "\(taken)/\(total) scheduled doses logged"
    }

    var selectedMedicationCounts: [String: Int] {
        guard let monthState else { return [:] }
        return Dictionary(uniqueKeysWithValues: monthState.medicationDays
            .filter { $0.date == selectedDateOnly }
            .map { ($0.medKey, $0.taken) })
    }

    var selectedProteinShakeCount: Int {
        guard let entry = todayEntries.first(where: { $0.habitKey == "protein_shake" }),
              let firstWord = entry.summary.split(separator: " ").first,
              let parsed = Int(firstWord) else {
            return 1
        }
        return min(20, max(0, parsed))
    }

    var connectionStatus: ConnectionStatus {
        if isLoading { return .connecting }
        if lastConnectionError != nil { return .unreachable }
        if monthState != nil { return .connected }
        return .unknown
    }

    func presentNotice(_ notice: AppNotice, autoDismissAfter seconds: Double = 4.0) {
        self.notice = notice
        Haptic.medium()
        Task {
            try? await Task.sleep(for: .seconds(seconds))
            await MainActor.run {
                if self.notice?.id == notice.id {
                    withAnimation(.smooth) {
                        self.notice = nil
                    }
                }
            }
        }
    }

    func refresh() async {
        let month = selectedMonth
        isLoading = true
        defer { isLoading = false }

        do {
            let client = try makeClient()
            let state = try await client.monthState(month: month)
            // Apply the result only while the selection still points at the
            // requested month, so a slower in-flight fetch never overwrites a
            // newer one.
            guard month == selectedMonth else { return }
            monthState = state
            lastConnectionError = nil
            notice = nil
        } catch {
            guard month == selectedMonth else { return }
            let message = readable(error)
            lastConnectionError = message
            notice = AppNotice(kind: .error, message: message)
            Haptic.error()
        }
    }

    func saveMedication(counts: [String: Int]) async {
        isSavingMedication = true
        defer { isSavingMedication = false }

        do {
            let payload = MedicationLogInput(
                localDate: selectedDateOnly,
                timezone: selectedTimeZone.identifier,
                doses: medicationGroups.flatMap { group in
                    group.meds.map { med in
                        MedicationDoseInput(
                            medKey: med.key,
                            medLabel: med.label,
                            takenCount: max(0, counts[med.key] ?? 0),
                            scheduledCount: med.total,
                            prn: med.prn
                        )
                    }
                }
            )

            let client = try makeClient()
            let response = try await client.logMedication(payload)

            if recomputeAfterMedicationSave {
                try await client.recompute(month: response.month)
            }

            monthState = try await client.monthState(month: response.month)
            lastConnectionError = nil
            notice = AppNotice(
                kind: .success,
                message: recomputeAfterMedicationSave
                    ? "Saved medication log and updated habits for \(response.month)."
                    : "Saved medication log for \(response.localDate.value)."
            )
            Haptic.success()
        } catch {
            notice = AppNotice(kind: .error, message: readable(error))
            Haptic.error()
        }
    }

    func saveProteinShake(count: Int) async {
        isSavingProteinShake = true
        defer { isSavingProteinShake = false }

        do {
            let payload = ProteinShakeLogInput(
                localDate: selectedDateOnly,
                timezone: selectedTimeZone.identifier,
                count: max(0, count)
            )

            let client = try makeClient()
            let response = try await client.logProteinShake(payload)

            if recomputeAfterProteinShakeSave {
                try await client.recompute(month: response.month)
            }

            monthState = try await client.monthState(month: response.month)
            lastConnectionError = nil
            notice = AppNotice(
                kind: .success,
                message: recomputeAfterProteinShakeSave
                    ? "Saved protein shake log and updated habits for \(response.month)."
                    : "Saved protein shake log for \(response.localDate.value)."
            )
            Haptic.success()
        } catch {
            notice = AppNotice(kind: .error, message: readable(error))
            Haptic.error()
        }
    }

    func dismissNotice() {
        withAnimation(.smooth) {
            notice = nil
        }
    }

    private func makeClient() throws -> HabitOSAPIClient {
        try HabitOSAPIClient(baseURLString: apiBaseURL, mobileAPIKey: mobileAPIKey)
    }

    private func readable(_ error: Error) -> String {
        if let urlError = error as? URLError {
            switch urlError.code {
            case .cannotConnectToHost, .notConnectedToInternet, .networkConnectionLost, .timedOut:
                return "Cannot reach HabitOS API at \(apiBaseURL). Check the URL, mobile key, and network, then retry."
            default:
                return urlError.localizedDescription
            }
        }

        if let localized = error as? LocalizedError, let description = localized.errorDescription {
            return description
        }
        return error.localizedDescription
    }
}

enum ConnectionStatus: Equatable {
    case unknown
    case connecting
    case connected
    case unreachable

    var label: String {
        switch self {
        case .unknown: "Not checked"
        case .connecting: "Connecting…"
        case .connected: "Connected"
        case .unreachable: "Unreachable"
        }
    }

    var color: Color {
        switch self {
        case .unknown: Color.inkGhost
        case .connecting: Color.accent
        case .connected: Color.accentHot
        case .unreachable: Color.anomaly
        }
    }
}

struct AppNotice: Identifiable, Equatable {
    enum Kind: Equatable {
        case success
        case error
        case info
    }

    let id = UUID()
    let kind: Kind
    let message: String
}
