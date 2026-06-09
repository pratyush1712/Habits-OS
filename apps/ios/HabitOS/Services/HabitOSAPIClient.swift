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
        print("[HabitOSAPI] initialized baseURL=\(url.absoluteString) apiKey=\(self.mobileAPIKey.isEmpty ? "none" : "set")")
    }

    func monthState(month: String) async throws -> MonthHabitState {
        try await request(path: "/state/month", query: [URLQueryItem(name: "month", value: month)])
    }

    func logMedication(_ payload: MedicationLogInput) async throws -> MedicationLogResponse {
        try await request(path: "/events/medication", method: "POST", body: payload)
    }

    func logProteinShake(_ payload: ProteinShakeLogInput) async throws -> ProteinShakeLogResponse {
        try await request(path: "/events/protein-shake", method: "POST", body: payload)
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
            print("[HabitOSAPI] failed to build URL for path=\(path)")
            throw HabitOSAPIError.invalidBaseURL(baseURL.absoluteString)
        }

        print("[HabitOSAPI] → \(method) \(url.absoluteString)")

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if !mobileAPIKey.isEmpty {
            request.setValue(mobileAPIKey, forHTTPHeaderField: "X-HabitOS-Mobile-Key")
            print("[HabitOSAPI]   auth: X-HabitOS-Mobile-Key present")
        }

        if let body {
            let encoder = JSONEncoder.habitOS
            request.httpBody = try encoder.encode(AnyEncodable(body))
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            if let bodyPreview = String(data: request.httpBody ?? Data(), encoding: .utf8) {
                print("[HabitOSAPI]   body: \(bodyPreview)")
            }
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            print("[HabitOSAPI] ← invalid response (not HTTPURLResponse)")
            throw HabitOSAPIError.invalidResponse
        }

        let responsePreview = String(data: data, encoding: .utf8) ?? "<\(data.count) bytes, non-UTF8>"
        let truncatedPreview = responsePreview.count > 500
            ? String(responsePreview.prefix(500)) + "…"
            : responsePreview
        print("[HabitOSAPI] ← \(http.statusCode) (\(data.count) bytes) \(truncatedPreview)")

        guard 200..<300 ~= http.statusCode else {
            let message = Self.errorMessage(from: data)
            print("[HabitOSAPI] ✗ server error \(http.statusCode): \(message)")
            throw HabitOSAPIError.server(statusCode: http.statusCode, message: message)
        }

        do {
            let decoded = try JSONDecoder.habitOS.decode(Response.self, from: data)
            print("[HabitOSAPI] ✓ decoded \(String(describing: Response.self))")
            return decoded
        } catch {
            let detail = Self.decodingDebugDescription(error)
            print("[HabitOSAPI] ✗ decode failed for \(String(describing: Response.self)): \(detail)")
            throw HabitOSAPIError.decoding(detail)
        }
    }

    private static func decodingDebugDescription(_ error: Error) -> String {
        guard let decodingError = error as? DecodingError else {
            return error.localizedDescription
        }

        switch decodingError {
        case .keyNotFound(let key, let context):
            return "missing key \"\(key.stringValue)\" at \(codingPath(context.codingPath))"
        case .typeMismatch(let type, let context):
            return "type mismatch for \(type) at \(codingPath(context.codingPath))"
        case .valueNotFound(let type, let context):
            return "missing value for \(type) at \(codingPath(context.codingPath))"
        case .dataCorrupted(let context):
            return "corrupt data at \(codingPath(context.codingPath)): \(context.debugDescription)"
        @unknown default:
            return decodingError.localizedDescription
        }
    }

    private static func codingPath(_ path: [CodingKey]) -> String {
        guard !path.isEmpty else {
            return "<root>"
        }
        return path.map(\.stringValue).joined(separator: ".")
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
