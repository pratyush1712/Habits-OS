import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var viewModel: AppViewModel

    var body: some View {
        TabView {
            NavigationStack {
                TodayView()
            }
            .tabItem {
                Label("Today", systemImage: "checklist")
            }

            NavigationStack {
                MedicationLogView()
            }
            .tabItem {
                Label("Meds", systemImage: "pills")
            }

            NavigationStack {
                SettingsView()
            }
            .tabItem {
                Label("Settings", systemImage: "slider.horizontal.3")
            }
        }
        .tint(.accentColor)
        .task {
            await viewModel.refresh()
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppViewModel())
}
