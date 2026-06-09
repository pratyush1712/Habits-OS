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
                ProteinShakeLogView()
            }
            .tabItem {
                Label("Shake", systemImage: "cup.and.saucer")
            }

            NavigationStack {
                SettingsView()
            }
            .tabItem {
                Label("Settings", systemImage: "slider.horizontal.3")
            }
        }
        .tint(Color.accent)
        .task {
            await viewModel.refresh()
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppViewModel())
}
