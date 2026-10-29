import Foundation

/// Bounds source previews to 1 MiB so generated files cannot stall Finder.
enum SourceContent {
    case text(String, truncated: Bool)
    case video

    static func read(from url: URL) throws -> SourceContent {
        let maximumBytes = 1_048_576
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let bytes = try handle.read(upToCount: maximumBytes + 4) ?? Data()
        let truncated = bytes.count > maximumBytes
        let preview = Data(bytes.prefix(maximumBytes))

        // Check UTF-32 first: its little-endian BOM starts with the UTF-16 BOM.
        let encodings: [(bom: [UInt8], encoding: String.Encoding, unit: Int, tail: Int)] = [
            ([0xFF, 0xFE, 0x00, 0x00], .utf32LittleEndian, 4, 0),
            ([0x00, 0x00, 0xFE, 0xFF], .utf32BigEndian, 4, 0),
            ([0xFF, 0xFE], .utf16LittleEndian, 2, 2),
            ([0xFE, 0xFF], .utf16BigEndian, 2, 2),
            ([0xEF, 0xBB, 0xBF], .utf8, 1, 3),
        ]
        for candidate in encodings where preview.starts(with: candidate.bom) {
            let payload = Data(preview.dropFirst(candidate.bom.count))
            if let source = decode(
                payload, encoding: candidate.encoding, truncated: truncated,
                unit: candidate.unit, maximumTail: candidate.tail
            ) {
                return .text(source, truncated: truncated)
            }
            return .video
        }

        // ECMAScript permits HT, LF, VT, FF, and CR in source whitespace.
        if preview.contains(where: { $0 < 0x20 && !(9...13).contains($0) }) {
            return .video
        }
        if let source = decode(preview, encoding: .utf8, truncated: truncated, unit: 1, maximumTail: 3) {
            return .text(source, truncated: truncated)
        }
        if let source = String(data: preview, encoding: .windowsCP1252) {
            return .text(source, truncated: truncated)
        }
        return .video
    }

    private static func decode(
        _ data: Data, encoding: String.Encoding, truncated: Bool,
        unit: Int, maximumTail: Int
    ) -> String? {
        // Truncation may bisect a UTF-8 sequence or UTF-16 surrogate pair.
        let lastTail = truncated ? maximumTail : 0
        for tail in stride(from: 0, through: lastTail, by: unit) where tail <= data.count {
            if let source = String(data: data.dropLast(tail), encoding: encoding) {
                return source
            }
        }
        return nil
    }
}
