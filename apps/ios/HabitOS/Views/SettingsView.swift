import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var viewModel: AppViewModel

    var body: some View {
        Form {
            Section("Admin API") {
                TextField("Base URL", text: $viewModel.apiBaseURL)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()
                SecureField("Mobile API key (optional)", text: $viewModel.mobileAPIKey)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                Button("Test connection") {
                    Task { await viewModel.refresh() }
                }
                Text("Default: https://habits.pratyushsudhakar.com/api/mobile. If HABITOS_MOBILE_API_KEY is configured on Vercel, paste that key here.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            Section("Local day") {
                TextField("Timezone", text: $viewModel.timezoneIdentifier)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
            }

            Section("Medication") {
                Toggle("Recompute after save", isOn: $viewModel.recomputeAfterMedicationSave)
                Text("Saving writes a medication source event through the admin mobile API, then optionally recomputes the month.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let notice = viewModel.notice {
                Section("Status") {
                    NoticeBanner(notice: notice)
                }
            }
        }
        .navigationTitle("Settings")
    }
}
