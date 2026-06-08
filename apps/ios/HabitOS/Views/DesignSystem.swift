import SwiftUI

// MARK: — Colors (ported from packages/design-tokens/tokens.json)

extension Color {
    static let paper = Color(hex: "#F5F0E8")
    static let paperDeep = Color(hex: "#E8DED0")
    static let rule = Color(hex: "#2A2A30")
    static let ruleSoft = Color(hex: "#B8B0A4")
    static let ink = Color(hex: "#242429")
    static let inkMid = Color(hex: "#3F3F48")
    static let inkFaint = Color(hex: "#5C5C66")
    static let inkGhost = Color(hex: "#82828F")
    static let accent = Color(hex: "#3B6BC0")
    static let accentHot = Color(hex: "#2ECC71")
    static let warningPanel = Color(hex: "#F5E6C8")
    static let bluePanel = Color(hex: "#C8D8F0")
    static let greenPanel = Color(hex: "#B8E6C8")
    static let redPanel = Color(hex: "#C8503C")
    static let anomaly = Color(hex: "#B04030")

    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: — Typography (ported from tokens.json)

enum HabitOSFont {
    static let family = "Helvetica Neue"
    static let fallback = "Arial"

    static func custom(size: CGFloat, weight: Font.Weight = .bold) -> Font {
        Font.custom(family, size: size).weight(weight)
    }

    static let display = custom(size: 64, weight: .black)
    static let h1 = custom(size: 32, weight: .black)
    static let h2 = custom(size: 24, weight: .heavy)
    static let h3 = custom(size: 18, weight: .heavy)
    static let body = custom(size: 16, weight: .bold)
    static let data = custom(size: 15, weight: .bold)
    static let meta = custom(size: 12, weight: .heavy)
    static let monoLabel = Font.system(size: 12, weight: .black, design: .monospaced)
        .smallCaps()
}

// MARK: — Grid Background

struct GridBackground: View {
    let gridSize: CGFloat = 36
    let lineOpacity: Double = 0.08

    var body: some View {
        GeometryReader { geometry in
            Canvas { context, size in
                let lineColor = Color.rule.opacity(lineOpacity)

                for x in stride(from: 0, to: size.width, by: gridSize) {
                    var path = Path()
                    path.move(to: CGPoint(x: x, y: 0))
                    path.addLine(to: CGPoint(x: x, y: size.height))
                    context.stroke(path, with: .color(lineColor), lineWidth: 1)
                }

                for y in stride(from: 0, to: size.height, by: gridSize) {
                    var path = Path()
                    path.move(to: CGPoint(x: 0, y: y))
                    path.addLine(to: CGPoint(x: size.width, y: y))
                    context.stroke(path, with: .color(lineColor), lineWidth: 1)
                }
            }
            .background(Color.paper)
        }
        .ignoresSafeArea()
    }
}

// MARK: — Panel (brutalist: 4px border, zero radius, white fill)

struct PaperPanel<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white)
            .overlay(
                Rectangle()
                    .stroke(Color.rule, lineWidth: 4)
            )
    }
}

// MARK: — Button Styles

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(HabitOSFont.h3)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .minHeight(56)
            .background(Color.rule)
            .overlay(
                Rectangle()
                    .stroke(Color.rule, lineWidth: 4)
            )
            .opacity(configuration.isPressed ? 0.85 : 1)
            .animation(.easeOut(duration: 0.08), value: configuration.isPressed)
    }
}

struct SecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(HabitOSFont.body)
            .foregroundStyle(Color.ink)
            .frame(maxWidth: .infinity)
            .minHeight(48)
            .background(Color.paper)
            .overlay(
                Rectangle()
                    .stroke(Color.rule, lineWidth: 4)
            )
            .opacity(configuration.isPressed ? 0.8 : 1)
            .animation(.easeOut(duration: 0.08), value: configuration.isPressed)
    }
}

struct CountButtonStyle: ButtonStyle {
    let filled: Bool

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(HabitOSFont.body)
            .foregroundStyle(filled ? .white : Color.ink)
            .frame(width: 52, height: 52)
            .background(filled ? Color.rule : Color.white)
            .overlay(
                Rectangle()
                    .stroke(Color.rule, lineWidth: 4)
            )
            .opacity(configuration.isPressed ? 0.8 : 1)
            .animation(.easeOut(duration: 0.08), value: configuration.isPressed)
    }
}

// MARK: — Notice Banner (brutalist)

struct NoticeBanner: View {
    let notice: AppNotice
    var onDismiss: (() -> Void)? = nil

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: iconName)
                .font(HabitOSFont.body)
                .foregroundStyle(foreground)
                .frame(width: 28, height: 28)

            Text(notice.message)
                .font(HabitOSFont.body)
                .foregroundStyle(foreground)
                .fixedSize(horizontal: false, vertical: true)

            Spacer(minLength: 0)

            if onDismiss != nil {
                Button {
                    onDismiss?()
                } label: {
                    Image(systemName: "xmark")
                        .font(HabitOSFont.data)
                        .foregroundStyle(foreground.opacity(0.7))
                        .frame(width: 28, height: 28)
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(background)
        .overlay(
            Rectangle()
                .stroke(Color.rule, lineWidth: 4)
        )
        .accessibilityElement(children: .combine)
    }

    private var iconName: String {
        switch notice.kind {
        case .success: "checkmark.square.fill"
        case .error: "exclamationmark.triangle.fill"
        case .info: "info.square.fill"
        }
    }

    private var background: Color {
        switch notice.kind {
        case .success: Color.greenPanel
        case .error: Color.redPanel
        case .info: Color.bluePanel
        }
    }

    private var foreground: Color {
        switch notice.kind {
        case .success: Color.ink
        case .error: Color.white
        case .info: Color.ink
        }
    }
}

// MARK: — Connection Help Panel

struct ConnectionHelpPanel: View {
    let baseURL: String
    let retry: () -> Void

    var body: some View {
        PaperPanel {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 10) {
                    Image(systemName: "network.slash")
                        .font(HabitOSFont.h3)
                        .foregroundStyle(Color.anomaly)
                    Text("HabitOS API is not connected")
                        .font(HabitOSFont.h3)
                        .foregroundStyle(Color.ink)
                }

                Text("The app is trying to reach \(baseURL). Use the hosted admin mobile API, then tap Retry.")
                    .font(HabitOSFont.body)
                    .foregroundStyle(Color.inkMid)
                    .fixedSize(horizontal: false, vertical: true)

                VStack(alignment: .leading, spacing: 8) {
                    Text("Expected URL")
                        .font(HabitOSFont.meta)
                        .foregroundStyle(Color.inkFaint)
                    Text("https://habits.pratyushsudhakar.com/api/mobile")
                        .font(HabitOSFont.data)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                        .background(Color.paperDeep)
                        .overlay(Rectangle().stroke(Color.rule, lineWidth: 2))
                    Text("If Vercel has HABITOS_MOBILE_API_KEY set, add the same key in Settings. Otherwise leave the key blank.")
                        .font(HabitOSFont.data)
                        .foregroundStyle(Color.inkFaint)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Button("Retry connection", action: retry)
                    .buttonStyle(PrimaryButtonStyle())
            }
        }
    }
}

// MARK: — Loading Rows

struct LoadingRows: View {
    var body: some View {
        VStack(spacing: 12) {
            ForEach(0..<4, id: \.self) { _ in
                Rectangle()
                    .fill(Color.rule.opacity(0.10))
                    .frame(height: 54)
                    .redacted(reason: .placeholder)
            }
        }
        .accessibilityLabel("Loading")
    }
}

// MARK: — Haptics

enum Haptic {
    @MainActor
    static func light() {
        #if os(iOS)
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()
        #endif
    }

    @MainActor
    static func medium() {
        #if os(iOS)
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.impactOccurred()
        #endif
    }

    @MainActor
    static func success() {
        #if os(iOS)
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
        #endif
    }

    @MainActor
    static func error() {
        #if os(iOS)
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.error)
        #endif
    }
}

// MARK: — View Modifiers

private extension View {
    func minHeight(_ value: CGFloat) -> some View {
        frame(minHeight: value)
    }
}

extension View {
    func habitOSBody() -> some View {
        self
            .font(HabitOSFont.body)
            .foregroundStyle(Color.ink)
    }
}
