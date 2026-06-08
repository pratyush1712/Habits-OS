import SwiftUI

enum HabitOSDesign {
    static let accent = Color.blue
    static let success = Color.green
    static let warning = Color.orange
    static let danger = Color.red
}

struct Panel<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(uiColor: .secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.primary.opacity(0.08), lineWidth: 1)
            )
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.title3.weight(.bold))
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .minHeight(56)
            .background(Color.accentColor)
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.smooth(duration: 0.14), value: configuration.isPressed)
    }
}

struct NoticeBanner: View {
    let notice: AppNotice

    var body: some View {
        Label {
            Text(notice.message)
                .font(.body.weight(.semibold))
                .fixedSize(horizontal: false, vertical: true)
        } icon: {
            Image(systemName: iconName)
        }
        .foregroundStyle(foreground)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(background)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .accessibilityElement(children: .combine)
    }

    private var iconName: String {
        switch notice.kind {
        case .success: "checkmark.circle.fill"
        case .error: "exclamationmark.triangle.fill"
        case .info: "info.circle.fill"
        }
    }

    private var background: Color {
        switch notice.kind {
        case .success: HabitOSDesign.success.opacity(0.15)
        case .error: HabitOSDesign.danger.opacity(0.14)
        case .info: HabitOSDesign.accent.opacity(0.13)
        }
    }

    private var foreground: Color {
        switch notice.kind {
        case .success: HabitOSDesign.success
        case .error: HabitOSDesign.danger
        case .info: HabitOSDesign.accent
        }
    }
}

struct ConnectionHelpPanel: View {
    let baseURL: String
    let retry: () -> Void

    var body: some View {
        Panel {
            VStack(alignment: .leading, spacing: 14) {
                Label("HabitOS API is not connected", systemImage: "network.slash")
                    .font(.title3.weight(.bold))
                    .foregroundStyle(.primary)
                Text("The app is trying to reach \(baseURL). Use the hosted admin mobile API, then tap Retry.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                VStack(alignment: .leading, spacing: 8) {
                    Text("Expected URL")
                        .font(.subheadline.weight(.semibold))
                    Text("https://habits.pratyushsudhakar.com/api/mobile")
                        .font(.footnote.monospaced().weight(.semibold))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Color(uiColor: .tertiarySystemGroupedBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    Text("If Vercel has HABITOS_MOBILE_API_KEY set, add the same key in Settings. Otherwise leave the key blank.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Button("Retry connection", action: retry)
                    .buttonStyle(PrimaryButtonStyle())
            }
        }
    }
}

struct LoadingRows: View {
    var body: some View {
        VStack(spacing: 12) {
            ForEach(0..<4, id: \.self) { _ in
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color.primary.opacity(0.10))
                    .frame(height: 54)
                    .redacted(reason: .placeholder)
            }
        }
        .accessibilityLabel("Loading")
    }
}

private extension View {
    func minHeight(_ value: CGFloat) -> some View {
        frame(minHeight: value)
    }
}
