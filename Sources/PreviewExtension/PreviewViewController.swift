import AVKit
import Cocoa
import OSLog
import Quartz

/// File-based previewing is required because macOS classifies .ts as video.
final class PreviewViewController: NSViewController, QLPreviewingController {
    private let logger = Logger(subsystem: Bundle.main.bundleIdentifier ?? "io.github.agustif.quicklook-typescript.Preview", category: "preview")
    private var requestID = UUID()
    private var player: AVPlayer?

    override func loadView() {
        view = NSView(frame: NSRect(x: 0, y: 0, width: 900, height: 650))
        preferredContentSize = NSSize(width: 900, height: 650)
    }

    func preparePreviewOfFile(at url: URL, completionHandler handler: @escaping (Error?) -> Void) {
        loadViewIfNeeded()
        let request = UUID()
        requestID = request
        player?.pause()
        player = nil
        logger.notice("Preparing native preview for extension: \(url.pathExtension, privacy: .public)")

        DispatchQueue.global(qos: .userInitiated).async {
            let result = Result { try SourceContent.read(from: url) }
            DispatchQueue.main.async {
                guard self.requestID == request else {
                    handler(NSError(domain: NSCocoaErrorDomain, code: NSUserCancelledError))
                    return
                }
                self.view.subviews.forEach { $0.removeFromSuperview() }
                switch result {
                case .success(.text(let source, let truncated)):
                    self.showSource(source, truncated: truncated)
                    self.logger.notice("Native source preview ready; truncated: \(truncated)")
                    handler(nil)
                case .success(.video):
                    let video = AVPlayerView(frame: self.view.bounds)
                    video.autoresizingMask = [.width, .height]
                    video.controlsStyle = .inline
                    let player = AVPlayer(url: url)
                    video.player = player
                    self.player = player
                    self.view.addSubview(video)
                    self.logger.notice("Binary transport stream routed to the native video player")
                    handler(nil)
                case .failure(let error):
                    self.logger.error("Source preview failed: \(error.localizedDescription, privacy: .public)")
                    handler(error)
                }
            }
        }
    }

    private func showSource(_ source: String, truncated: Bool) {
        let noticeHeight: CGFloat = truncated ? 30 : 0
        let scroll = NSScrollView(frame: NSRect(
            x: 0, y: noticeHeight, width: view.bounds.width,
            height: view.bounds.height - noticeHeight
        ))
        scroll.autoresizingMask = [.width, .height]
        scroll.hasVerticalScroller = true
        scroll.hasHorizontalScroller = true
        scroll.autohidesScrollers = true

        let text = NSTextView(frame: scroll.bounds)
        text.isEditable = false
        text.isSelectable = true
        text.isRichText = false
        text.font = .monospacedSystemFont(ofSize: 14, weight: .regular)
        text.textColor = .textColor
        text.backgroundColor = .textBackgroundColor
        text.textContainerInset = NSSize(width: 18, height: 18)
        text.isHorizontallyResizable = true
        text.isVerticallyResizable = true
        text.autoresizingMask = [.width]
        text.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        text.textContainer?.containerSize = text.maxSize
        text.textContainer?.widthTracksTextView = false
        text.string = source
        scroll.documentView = text
        view.addSubview(scroll)

        if truncated {
            let notice = NSTextField(labelWithString: "Preview limited to the first 1 MiB of this file.")
            notice.frame = NSRect(x: 18, y: 7, width: view.bounds.width - 36, height: 18)
            notice.autoresizingMask = [.width]
            notice.textColor = .secondaryLabelColor
            notice.font = .systemFont(ofSize: 11)
            view.addSubview(notice)
        }
    }

    deinit {
        player?.pause()
    }
}
