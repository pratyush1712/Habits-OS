import SwiftUI

@main
struct HabitOSApp: App {
    @StateObject private var viewModel = AppViewModel()

    init() {
        let ink = UIColor(Color.ink)
        UINavigationBar.appearance().titleTextAttributes = [.foregroundColor: ink]
        UINavigationBar.appearance().largeTitleTextAttributes = [.foregroundColor: ink]
        UINavigationBar.appearance().tintColor = ink
        UITextField.appearance().tintColor = ink
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(viewModel)
        }
    }
}
