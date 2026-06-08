import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var viewModel: AppViewModel

    var body: some View {
        Form {
            Section {
                HStack {
                    Text("Connection")
                        .font(.body)
                    Spacer()
                    HStack(spacing: 6) {
                        Circle()
                            .fill(viewModel.connectionStatus.color)
                            .frame(width: 8, height: 8)
                        Text(viewModel.connectionStatus.label)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(viewModel.connectionStatus.color)
                    }
                }

                TextField("Server URL", text: $viewModel.apiBaseURL)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()

                SecureField("API key (optional)", text: $viewModel.mobileAPIKey)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()

                Button {
                    Haptic.medium()
                    Task { await viewModel.refresh() }
                } label: {
                    HStack {
                        Text("Test connection")
                        if viewModel.isLoading {
                            Spacer()
                            ProgressView()
                        }
                    }
                }
                .disabled(viewModel.isLoading)
            } header: {
                Text("HabitOS Server")
            } footer: {
                Text("The URL should end in /api/mobile. If your server requires a mobile API key, paste it above.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("Timezone") {
                TextField("Identifier", text: $viewModel.timezoneIdentifier)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
            }

            Section {
                Toggle("Update habits after saving", isOn: $viewModel.recomputeAfterMedicationSave)
            } header: {
                Text("Medication")
            } footer: {
                Text("When on, saving medication automatically recomputes habit entries for the month.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let notice = viewModel.notice {
                Section("Status") {
                    NoticeBanner(notice: notice) {
                        viewModel.dismissNotice()
                    }
                }
            }

            Section {
                HStack {
                    Text("Version")
                        .font(.body)
                    Spacer()
                    Text(appVersion)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .monospaced()
                }
            }
        }
        .navigationTitle("Settings")
    }

    private var appVersion: String {
        let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "0"
        return "\(version) (\(build))"
    }
}
