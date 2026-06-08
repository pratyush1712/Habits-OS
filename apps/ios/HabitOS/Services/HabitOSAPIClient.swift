import Foundation

enum HabitOSAPIError: LocalizedError, Equatable {
    case invalidBaseURL(String)
    case invalidResponse
    case server(statusCode: Int, message: String)
    case decoding(String)

    var errorDescription: String? {
        switch self {
        case .invalidBaseURL(let value): "Invalid API base URL: \(value)"
        case .invalidResponse: "The server returned an invalid response."
        case .server(let statusCode, let message): "API \(statusCode): \(message)"
        case .decoding(let message): "Could not read API response: \(message)"
        }
    }
}

struct HabitOSAPIClient {
    var baseURL: URL
    var mobileAPIKey: String
    var session: URLSession = .shared

    init(baseURLString: String, mobileAPIKey: String = "", session: URLSession = .shared) throws {
        guard let url = URL(string: baseURLString.trimmingCharacters(in: .whitespacesAndNewlines)) else {
            throw HabitOSAPIError.invalidBaseURL(baseURLString)
        }
        baseURL = url
        self.mobileAPIKey = mobileAPIKey.trimmingCharacters(in: .whitespacesAndNewlines)
        self.session = session
    }

    func monthState(month: String) async throws -> MonthHabitState {
        try await request(path: "/state/month", query: [URLQueryItem(name: "month", value: month)])
    }

    func logMedication(_ payload: MedicationLogInput) async throws -> MedicationLogResponse {
        try await request(path: "/events/medication", method: "POST", body: payload)
    }

    func recompute(month: String) async throws {
        let _: EmptyResponse = try await request(path: "/habits/recompute", method: "POST", query: [URLQueryItem(name: "month", value: month)])
    }

    private func request<Response: Decodable>(
        path: String,
        method: String = "GET",
        query: [URLQueryItem] = [],
        body: (some Encodable)? = Optional<String>.none
    ) async throws -> Response {
        var components = URLComponents(url: baseURL.appending(path: path), resolvingAgainstBaseURL: false)
        components?.queryItems = query.isEmpty ? nil : query

        guard let url = components?.url else {
            throw HabitOSAPIError.invalidBaseURL(baseURL.absoluteString)
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if !mobileAPIKey.isEmpty {
            request.setValue(mobileAPIKey, forHTTPHeaderField: "X-HabitOS-Mobile-Key")
        }

        if let body {
            let encoder = JSONEncoder.habitOS
            request.httpBody = try encoder.encode(AnyEncodable(body))
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw HabitOSAPIError.invalidResponse
        }

        guard 200..<300 ~= http.statusCode else {
            throw HabitOSAPIError.server(statusCode: http.statusCode, message: Self.errorMessage(from: data))
        }

        do {
            return try JSONDecoder.habitOS.decode(Response.self, from: data)
        } catch {
            throw HabitOSAPIError.decoding(error.localizedDescription)
        }
    }

    private static func errorMessage(from data: Data) -> String {
        guard !data.isEmpty else {
            return "No response body."
        }

        if let decoded = try? JSONDecoder().decode(APIErrorEnvelope.self, from: data) {
            return decoded.detail
        }

        return String(data: data, encoding: .utf8) ?? "Unreadable response body."
    }
}

private struct AnyEncodable: Encodable {
    private let encodeValue: (Encoder) throws -> Void

    init(_ wrapped: some Encodable) {
        encodeValue = wrapped.encode(to:)
    }

    func encode(to encoder: Encoder) throws {
        try encodeValue(encoder)
    }
}

private struct APIErrorEnvelope: Decodable {
    let detail: String
}

private struct EmptyResponse: Decodable {
}

extension JSONDecoder {
    static var habitOS: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let value = try container.decode(String.self)

            if let date = ISO8601DateFormatter.habitOSFormatter(fractionalSeconds: true).date(from: value) {
                return date
            }
            if let date = ISO8601DateFormatter.habitOSFormatter(fractionalSeconds: false).date(from: value) {
                return date
            }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid ISO-8601 date: \(value)")
        }
        return decoder
    }
}

extension JSONEncoder {
    static var habitOS: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }
}

extension ISO8601DateFormatter {
    static func habitOSFormatter(fractionalSeconds: Bool) -> ISO8601DateFormatter {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = fractionalSeconds
            ? [.withInternetDateTime, .withFractionalSeconds]
            : [.withInternetDateTime]
        return formatter
    }
}
