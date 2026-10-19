// macOS Vision OCR helper.
// Usage: ocr <image1> [image2 ...]
// Prints "===FILE:<path>" followed by recognized lines, sorted top-to-bottom.
import Foundation
import Vision
import AppKit

struct Line {
    let text: String
    let x: CGFloat
    let y: CGFloat
    let conf: Float
}

func ocr(_ path: String) -> [Line] {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("ERR_LOAD \(path)\n".data(using: .utf8)!)
        return []
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
    req.usesLanguageCorrection = true
    req.minimumTextHeight = 0.008
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([req]) } catch {
        FileHandle.standardError.write("ERR_OCR \(path) \(error)\n".data(using: .utf8)!)
        return []
    }
    var out: [Line] = []
    for obs in (req.results ?? []) {
        guard let c = obs.topCandidates(1).first else { continue }
        if c.confidence < 0.25 { continue }
        let bb = obs.boundingBox
        out.append(Line(text: c.string, x: bb.minX, y: 1.0 - bb.maxY, conf: c.confidence))
    }
    // top-to-bottom, then left-to-right; cluster lines within 1.2% of page height
    out.sort { a, b in
        if abs(a.y - b.y) < 0.012 { return a.x < b.x }
        return a.y < b.y
    }
    return out
}

let files = Array(CommandLine.arguments.dropFirst())
if files.isEmpty { print("usage: ocr <image> [image...]"); exit(2) }
for f in files {
    print("===FILE:\(f)")
    for l in ocr(f) { print(l.text) }
}
