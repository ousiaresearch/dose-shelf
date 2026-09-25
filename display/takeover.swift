// dose-shelf — the presentation layer. A bounded fullscreen takeover: an artefact takes the screen
// for a stated number of seconds, then leaves. Nothing is installed, nothing is persisted, no state
// is kept, no keyboard events are captured, no window survives the process.
//
//   takeover <file> <seconds> [label]
//
// Dismiss: any key, any click, or the timer. Exit code 0 either way.

import AppKit
import Foundation

final class Overlay: NSObject, NSApplicationDelegate {
    let path: String
    let seconds: Double
    let label: String
    var window: NSWindow!

    init(path: String, seconds: Double, label: String) {
        self.path = path; self.seconds = seconds; self.label = label
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        guard let screen = NSScreen.main else { NSApp.terminate(nil); return }
        window = NSWindow(contentRect: screen.frame, styleMask: [.borderless],
                          backing: .buffered, defer: false, screen: screen)
        window.level = .screenSaver          // above everything, including the Dock and menu bar
        window.backgroundColor = NSColor.black
        window.isOpaque = true
        window.hasShadow = false
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]

        let host = NSView(frame: screen.frame)
        host.wantsLayer = true
        host.layer?.backgroundColor = NSColor.black.cgColor

        if let image = NSImage(contentsOfFile: path) {
            let iv = NSImageView(frame: screen.frame.insetBy(dx: 0, dy: 0))
            iv.image = image
            iv.imageScaling = .scaleProportionallyUpOrDown
            iv.animates = true                       // animated GIFs play
            iv.autoresizingMask = [.width, .height]
            host.addSubview(iv)
            // NSImageView centres by default; keep a black matte around the frame
        } else {
            let tf = NSTextField(labelWithString: "artefact unreadable as an image: \(path)")
            tf.textColor = .white; tf.frame = screen.frame
            tf.alignment = .center
            host.addSubview(tf)
        }

        if !label.isEmpty {
            let tf = NSTextField(labelWithString: label)
            tf.textColor = NSColor(white: 1.0, alpha: 0.55)
            tf.font = NSFont.monospacedSystemFont(ofSize: 15, weight: .regular)
            tf.alignment = .center
            tf.frame = NSRect(x: 0, y: 28, width: screen.frame.width, height: 22)
            tf.autoresizingMask = [.width, .maxYMargin]
            host.addSubview(tf)
        }
        window.contentView = host
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // any key or click dismisses; the timer dismisses otherwise
        NSEvent.addGlobalMonitorForEvents(matching: [.keyDown, .leftMouseDown, .rightMouseDown]) { _ in
            NSApp.terminate(nil)
        }
        NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .leftMouseDown, .rightMouseDown]) { _ in
            NSApp.terminate(nil); return nil
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + seconds) { NSApp.terminate(nil) }
    }
}

let args = CommandLine.arguments
guard args.count >= 3, let secs = Double(args[2]) else {
    FileHandle.standardError.write("usage: takeover <file> <seconds> [label]\n".data(using: .utf8)!)
    exit(2)
}
let app = NSApplication.shared
let delegate = Overlay(path: args[1], seconds: secs, label: args.count > 3 ? args[3] : "")
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
