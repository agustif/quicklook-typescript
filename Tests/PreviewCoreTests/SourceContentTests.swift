import Foundation
import XCTest
@testable import PreviewCore

final class SourceContentTests: XCTestCase {
    private func withFile(_ data: Data, check: (URL) throws -> Void) throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let file = directory.appendingPathComponent("example.ts")
        try data.write(to: file)
        try check(file)
        XCTAssertEqual(try Data(contentsOf: file), data, "Previewing must not modify the source")
    }

    private func assertText(_ data: Data, equals expected: String, truncated expectedTruncation: Bool = false) throws {
        try withFile(data) { file in
            guard case .text(let source, let truncated) = try SourceContent.read(from: file) else {
                return XCTFail("Source was classified as video")
            }
            XCTAssertEqual(source, expected)
            XCTAssertEqual(truncated, expectedTruncation)
        }
    }

    func testUTF8Source() throws {
        let source = "export const greeting: string = \"España 🚀\";\n"
        try assertText(Data(source.utf8), equals: source)
    }

    func testEmptyFile() throws {
        try assertText(Data(), equals: "")
    }

    func testECMAScriptWhitespace() throws {
        let source = "let\u{000B}value = 1;\t\u{000C}\r\n"
        try assertText(Data(source.utf8), equals: source)
    }

    func testUTF8ByteOrderMark() throws {
        let source = "export const value = 1;\n"
        try assertText(Data([0xEF, 0xBB, 0xBF]) + Data(source.utf8), equals: source)
    }

    func testUTF16BothByteOrders() throws {
        let source = "export const greeting = \"España 🚀\";\n"
        for (bom, encoding): ([UInt8], String.Encoding) in [
            ([0xFF, 0xFE], .utf16LittleEndian), ([0xFE, 0xFF], .utf16BigEndian),
        ] {
            try assertText(Data(bom) + XCTUnwrap(source.data(using: encoding)), equals: source)
        }
    }

    func testUTF32BOMsAreNotMistakenForUTF16() throws {
        let source = "const greeting = \"España 🚀\";\n"
        for (bom, encoding): ([UInt8], String.Encoding) in [
            ([0xFF, 0xFE, 0x00, 0x00], .utf32LittleEndian),
            ([0x00, 0x00, 0xFE, 0xFF], .utf32BigEndian),
        ] {
            try assertText(Data(bom) + XCTUnwrap(source.data(using: encoding)), equals: source)
        }
    }

    func testWindows1252Fallback() throws {
        try assertText(Data([0x63, 0x61, 0x66, 0xE9]), equals: "café")
    }

    func testUTF8LimitDoesNotSplitACharacter() throws {
        let prefix = String(repeating: "x", count: 1_048_575)
        try assertText(Data((prefix + "€\n").utf8), equals: prefix, truncated: true)
    }

    func testUTF16LimitDoesNotSplitASurrogatePair() throws {
        let prefix = String(repeating: " ", count: 524_286)
        for (bom, encoding): ([UInt8], String.Encoding) in [
            ([0xFF, 0xFE], .utf16LittleEndian), ([0xFE, 0xFF], .utf16BigEndian),
        ] {
            let encoded = try XCTUnwrap((prefix + "🚀A").data(using: encoding))
            try assertText(Data(bom) + encoded, equals: prefix, truncated: true)
        }
    }

    func testUTF32LimitStaysOnACodePointBoundary() throws {
        let prefix = String(repeating: "x", count: (1_048_576 - 4) / 4)
        let encoded = try XCTUnwrap((prefix + "🚀").data(using: .utf32LittleEndian))
        try assertText(Data([0xFF, 0xFE, 0x00, 0x00]) + encoded, equals: prefix, truncated: true)
    }

    func testExactLimitIsNotMarkedAsTruncated() throws {
        let source = String(repeating: "x", count: 1_048_576)
        try assertText(Data(source.utf8), equals: source)
    }

    func testBinaryTransportStreamUsesTheVideoPath() throws {
        // Two MPEG-TS-sized packets with a sync byte, header, and binary payload.
        let packet = Data([0x47, 0x40, 0x00, 0x10]) + Data(repeating: 0xFF, count: 184)
        try withFile(packet + packet) { file in
            guard case .video = try SourceContent.read(from: file) else {
                return XCTFail("Binary transport stream was classified as source")
            }
        }
    }

    func testMissingFileReportsAnError() {
        let missing = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString).appendingPathComponent("missing.ts")
        XCTAssertThrowsError(try SourceContent.read(from: missing))
    }
}
