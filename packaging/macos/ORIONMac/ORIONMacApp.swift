import SwiftUI
import WebKit

@main
struct ORIONMacApp: App {
    var body: some Scene { WindowGroup { ORIONWebView() } }
}

struct ORIONWebView: NSViewRepresentable {
    func makeNSView(context: Context) -> WKWebView {
        let web = WKWebView()
        if let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "ui") {
            web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        }
        return web
    }
    func updateNSView(_ nsView: WKWebView, context: Context) {}
}
