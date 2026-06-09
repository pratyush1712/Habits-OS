import Foundation

enum HabitStatus: String, Codable, CaseIterable, Identifiable {
    case checked
    case partial
    case warning
    case missed
    case manual

    var id: String { rawValue }

    var label: String {
        switch self {
        case .checked: "Checked"
        case .partial: "Partial"
        case .warning: "Warning"
        case .missed: "Missed"
        case .manual: "Manual"
        }
    }
}

struct Habit: Codable, Identifiable, Hashable {
    let key: String
    let label: String
    let short: String
    let kind: String
    let enabled: Bool
    let metricOnly: Bool
    let sortOrder: Int
    let description: String
    let eventTypes: [String]
    let sources: [String]

    var id: String { key }

    enum CodingKeys: String, CodingKey {
        case key
        case label
        case short
        case kind
        case enabled
        case metricOnly = "metric_only"
        case sortOrder = "sort_order"
        case description
        case eventTypes = "event_types"
        case sources
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        key = try container.decode(String.self, forKey: .key)
        label = try container.decode(String.self, forKey: .label)
        short = try container.decode(String.self, forKey: .short)
        kind = try container.decodeIfPresent(String.self, forKey: .kind) ?? "auto"
        enabled = try container.decodeIfPresent(Bool.self, forKey: .enabled) ?? true
        metricOnly = try container.decodeIfPresent(Bool.self, forKey: .metricOnly) ?? false
        sortOrder = try container.decodeIfPresent(Int.self, forKey: .sortOrder) ?? 100
        description = try container.decodeIfPresent(String.self, forKey: .description) ?? ""
        eventTypes = try container.decodeIfPresent([String].self, forKey: .eventTypes) ?? []
        sources = try container.decodeIfPresent([String].self, forKey: .sources) ?? []
    }
}

struct HabitEntry: Codable, Identifiable, Hashable {
    let date: DateOnly
    let habitKey: String
    let status: HabitStatus
    let source: String
    let summary: String
    let description: String
    let confidence: Double
    let linkedSourceEventIDs: [String]
    let explanation: String
    let manuallyOverridden: Bool

    var id: String { "\(date.value)-\(habitKey)" }

    enum CodingKeys: String, CodingKey {
        case date
        case habitKey = "habit_key"
        case status
        case source
        case summary
        case description
        case confidence
        case linkedSourceEventIDs = "linked_source_event_ids"
        case explanation
        case manuallyOverridden = "manually_overridden"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        date = try container.decode(DateOnly.self, forKey: .date)
        habitKey = try container.decode(String.self, forKey: .habitKey)
        status = try container.decode(HabitStatus.self, forKey: .status)
        source = try container.decode(String.self, forKey: .source)
        summary = try container.decodeIfPresent(String.self, forKey: .summary) ?? ""
        description = try container.decodeIfPresent(String.self, forKey: .description) ?? ""
        confidence = try container.decodeIfPresent(Double.self, forKey: .confidence) ?? 1.0
        linkedSourceEventIDs = try container.decodeIfPresent([String].self, forKey: .linkedSourceEventIDs) ?? []
        explanation = try container.decodeIfPresent(String.self, forKey: .explanation) ?? ""
        manuallyOverridden = try container.decodeIfPresent(Bool.self, forKey: .manuallyOverridden) ?? false
    }
}

struct MedicationItem: Codable, Identifiable, Hashable {
    let key: String
    let label: String
    let short: String
    let dose: String
    let total: Int
    let prn: Bool

    var id: String { key }

    init(
        key: String,
        label: String,
        short: String,
        dose: String,
        total: Int,
        prn: Bool
    ) {
        self.key = key
        self.label = label
        self.short = short
        self.dose = dose
        self.total = total
        self.prn = prn
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        key = try container.decode(String.self, forKey: .key)
        label = try container.decode(String.self, forKey: .label)
        short = try container.decode(String.self, forKey: .short)
        dose = try container.decodeIfPresent(String.self, forKey: .dose) ?? ""
        total = try container.decodeIfPresent(Int.self, forKey: .total) ?? 1
        prn = try container.decodeIfPresent(Bool.self, forKey: .prn) ?? false
    }

    private enum CodingKeys: String, CodingKey {
        case key
        case label
        case short
        case dose
        case total
        case prn
    }
}

struct MedicationGroup: Codable, Identifiable, Hashable {
    let key: String
    let label: String
    let meds: [MedicationItem]

    var id: String { key }
}

struct MedicationDayDose: Codable, Identifiable, Hashable {
    let date: DateOnly
    let medKey: String
    let taken: Int
    let total: Int?
    let status: String?

    var id: String { "\(date.value)-\(medKey)" }

    enum CodingKeys: String, CodingKey {
        case date
        case medKey = "med_key"
        case taken
        case total
        case status
    }
}

struct MonthHabitState: Codable, Hashable {
    let month: String
    let habits: [Habit]
    let entries: [HabitEntry]
    let medicationGroups: [MedicationGroup]
    let medicationDays: [MedicationDayDose]
    let generatedAt: Date

    enum CodingKeys: String, CodingKey {
        case month
        case habits
        case entries
        case medicationGroups = "medication_groups"
        case medicationDays = "medication_days"
        case generatedAt = "generated_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        month = try container.decode(String.self, forKey: .month)
        habits = try container.decodeIfPresent([Habit].self, forKey: .habits) ?? []
        entries = try container.decodeIfPresent([HabitEntry].self, forKey: .entries) ?? []
        medicationGroups = try container.decodeIfPresent([MedicationGroup].self, forKey: .medicationGroups) ?? []
        medicationDays = try container.decodeIfPresent([MedicationDayDose].self, forKey: .medicationDays) ?? []
        generatedAt = try container.decodeIfPresent(Date.self, forKey: .generatedAt) ?? Date()
    }
}

struct MedicationDoseInput: Codable, Hashable {
    let medKey: String
    let medLabel: String
    let takenCount: Int
    let scheduledCount: Int
    let prn: Bool

    enum CodingKeys: String, CodingKey {
        case medKey = "med_key"
        case medLabel = "med_label"
        case takenCount = "taken_count"
        case scheduledCount = "scheduled_count"
        case prn
    }
}

struct MedicationLogInput: Codable, Hashable {
    let localDate: DateOnly
    let timezone: String
    let doses: [MedicationDoseInput]

    enum CodingKeys: String, CodingKey {
        case localDate = "local_date"
        case timezone
        case doses
    }
}

struct MedicationLogResponse: Codable, Hashable {
    let month: String
    let localDate: DateOnly
    let events: Int
    let inserted: Int
    let updated: Int

    enum CodingKeys: String, CodingKey {
        case month
        case localDate = "local_date"
        case events
        case inserted
        case updated
    }
}

struct ProteinShakeLogInput: Codable, Hashable {
    let localDate: DateOnly
    let timezone: String
    let count: Int

    enum CodingKeys: String, CodingKey {
        case localDate = "local_date"
        case timezone
        case count
    }
}

struct ProteinShakeLogResponse: Codable, Hashable {
    let month: String
    let localDate: DateOnly
    let count: Int
    let inserted: Int
    let updated: Int

    enum CodingKeys: String, CodingKey {
        case month
        case localDate = "local_date"
        case count
        case inserted
        case updated
    }
}

struct DateOnly: Codable, Hashable, Comparable, ExpressibleByStringLiteral {
    let value: String

    init(_ value: String) {
        self.value = value
    }

    init(stringLiteral value: StringLiteralType) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        value = try container.decode(String.self)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(value)
    }

    static func < (lhs: DateOnly, rhs: DateOnly) -> Bool {
        lhs.value < rhs.value
    }
}

extension DateOnly {
    static func today(timeZone: TimeZone = .current) -> DateOnly {
        DateOnly(Self.format(Date(), timeZone: timeZone))
    }

    static func monthString(for date: Date = Date(), timeZone: TimeZone = .current) -> String {
        String(format(date, timeZone: timeZone).prefix(7))
    }

    static func format(_ date: Date, timeZone: TimeZone = .current) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
}

extension MedicationGroup {
    static let fallbackPlan: [MedicationGroup] = [
        MedicationGroup(
            key: "morning",
            label: "Morning",
            meds: [
                MedicationItem(key: "propranolol_morning", label: "Propranolol", short: "Pro", dose: "morning dose", total: 1, prn: false),
                MedicationItem(key: "adderall_xr", label: "Adderall XR", short: "XR", dose: "30mg XR", total: 1, prn: false),
                MedicationItem(key: "multivitamin", label: "Multivitamin", short: "MV", dose: "2 pills with food", total: 2, prn: false)
            ]
        ),
        MedicationGroup(
            key: "afternoon",
            label: "Afternoon",
            meds: [
                MedicationItem(key: "adderall_ir", label: "Adderall IR", short: "IR", dose: "20mg IR", total: 1, prn: false),
                MedicationItem(key: "omega_3", label: "Omega 3", short: "O3", dose: "3 pills", total: 3, prn: false)
            ]
        ),
        MedicationGroup(
            key: "night",
            label: "Night",
            meds: [
                MedicationItem(key: "propranolol_night", label: "Propranolol", short: "Pro", dose: "night dose", total: 1, prn: false),
                MedicationItem(key: "magnesium", label: "Magnesium", short: "Mg", dose: "2 x 100mg", total: 2, prn: false),
                MedicationItem(key: "hydroxyzine", label: "Hydroxyzine", short: "Hyd", dose: "night / anxiety", total: 0, prn: true)
            ]
        )
    ]
}
