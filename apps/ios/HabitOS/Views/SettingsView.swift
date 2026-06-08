import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var viewModel: AppViewModel

    var body: some View {
        ZStack {
            GridBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    PaperPanel {
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Settings")
                                .font(HabitOSFont.h1)
                                .foregroundStyle(Color.ink)

                            HStack {
                                Text("Connection")
                                    .font(HabitOSFont.body)
                                    .foregroundStyle(Color.ink)
                                Spacer()
                                HStack(spacing: 6) {
                                    Rectangle()
                                        .fill(connectionColor)
                                        .frame(width: 8, height: 8)
                                    Text(viewModel.connectionStatus.label)
                                        .font(HabitOSFont.data)
                                        .foregroundStyle(connectionColor)
                                }
                            }

                            VStack(alignment: .leading, spacing: 6) {
                                Text("Server URL")
                                    .font(HabitOSFont.meta)
                                    .foregroundStyle(Color.inkFaint)
                                TextField("Server URL", text: $viewModel.apiBaseURL)
                                    .font(HabitOSFont.data)
                                    .foregroundStyle(Color.ink)
                                    .textInputAutocapitalization(.never)
                                    .keyboardType(.URL)
                                    .autocorrectionDisabled()
                                    .padding(12)
                                    .background(Color.paper)
                                    .overlay(Rectangle().stroke(Color.rule, lineWidth: 2))
                            }

                            VStack(alignment: .leading, spacing: 6) {
                                Text("API key (optional)")
                                    .font(HabitOSFont.meta)
                                    .foregroundStyle(Color.inkFaint)
                                SecureField("API key", text: $viewModel.mobileAPIKey)
                                    .font(HabitOSFont.data)
                                    .textInputAutocapitalization(.never)
                                    .autocorrectionDisabled()
                                    .padding(12)
                                    .background(Color.paper)
                                    .overlay(Rectangle().stroke(Color.rule, lineWidth: 2))
                            }

                            Button {
                                Haptic.medium()
                                Task { await viewModel.refresh() }
                            } label: {
                                HStack {
                                    Text("Test connection")
                                    if viewModel.isLoading {
                                        ProgressView()
                                            .tint(Color.ink)
                                    }
                                }
                            }
                            .buttonStyle(SecondaryButtonStyle())
                            .disabled(viewModel.isLoading)

                            Text("The URL should end in /api/mobile. If your server requires a mobile API key, paste it above.")
                                .font(HabitOSFont.meta)
                                .foregroundStyle(Color.inkFaint)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    PaperPanel {
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Timezone")
                                .font(HabitOSFont.h3)
                                .foregroundStyle(Color.ink)

                            VStack(alignment: .leading, spacing: 6) {
                                Text("Identifier")
                                    .font(HabitOSFont.meta)
                                    .foregroundStyle(Color.inkFaint)
                                TextField("Identifier", text: $viewModel.timezoneIdentifier)
                                    .font(HabitOSFont.data)
                                    .foregroundStyle(Color.ink)
                                    .textInputAutocapitalization(.never)
                                    .autocorrectionDisabled()
                                    .padding(12)
                                    .background(Color.paper)
                                    .overlay(Rectangle().stroke(Color.rule, lineWidth: 2))
                            }
                        }
                    }

                    PaperPanel {
                        VStack(alignment: .leading, spacing: 16) {
                            Text("Medication")
                                .font(HabitOSFont.h3)
                                .foregroundStyle(Color.ink)

                            Toggle("Update habits after saving", isOn: $viewModel.recomputeAfterMedicationSave)
                                .font(HabitOSFont.body)
                                .foregroundStyle(Color.ink)

                            Text("When on, saving medication automatically recomputes habit entries for the month.")
                                .font(HabitOSFont.meta)
                                .foregroundStyle(Color.inkFaint)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    if let notice = viewModel.notice {
                        NoticeBanner(notice: notice) {
                            viewModel.dismissNotice()
                        }
                    }

                    PaperPanel {
                        HStack {
                            Text("Version")
                                .font(HabitOSFont.body)
                                .foregroundStyle(Color.ink)
                            Spacer()
                            Text(appVersion)
                                .font(HabitOSFont.data)
                                .foregroundStyle(Color.inkFaint)
                                .monospaced()
                        }
                    }
                }
                .padding(18)
            }
        }
        .navigationTitle("Settings")
    }

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
        return "\(version) (\(build))"
    }

    private var connectionColor: Color {
        switch viewModel.connectionStatus {
        case .unknown: Color.inkGhost
        case .connecting: Color.accent
        case .connected: Color.accentHot
        case .unreachable: Color.anomaly
        }
    }
}
