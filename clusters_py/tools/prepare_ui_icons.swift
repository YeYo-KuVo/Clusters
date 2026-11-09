// Prepare antialiased display assets; retain all original files.
// swift -module-cache-path /tmp/hui-pu-swift-cache clusters_py/tools/prepare_ui_icons.swift clusters_py/assets/icons
import Foundation
import CoreGraphics
import ImageIO

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let output = root.appendingPathComponent("ui")
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
func load(_ name: String) -> CGImage {
    let source = CGImageSourceCreateWithURL(root.appendingPathComponent(name) as CFURL, nil)!
    return CGImageSourceCreateImageAtIndex(source, 0, nil)!
}
func bounds(_ image: CGImage) -> CGRect {
    let w = image.width, h = image.height
    var pixels = [UInt8](repeating: 0, count: w*h*4)
    var minX = w, minY = h, maxX = 0, maxY = 0
    pixels.withUnsafeMutableBytes { buffer in
        let context = CGContext(data: buffer.baseAddress, width: w, height: h,
                                bitsPerComponent: 8, bytesPerRow: w*4,
                                space: CGColorSpaceCreateDeviceRGB(),
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))
        for y in 0..<h { for x in 0..<w {
            if buffer[(y*w+x)*4+3] > 16 {
                minX = min(minX,x); minY = min(minY,y)
                maxX = max(maxX,x); maxY = max(maxY,y)
            }
        }}
    }
    return CGRect(x: minX, y: minY, width: maxX-minX+1, height: maxY-minY+1)
}
func save(_ image: CGImage, crop: CGRect, width: Int, height: Int, name: String, fitExactly: Bool = false) {
    let trimmed = image.cropping(to: crop)!
    let context = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8,
                            bytesPerRow: width*4, space: CGColorSpaceCreateDeviceRGB(),
                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    context.interpolationQuality = .high
    let scale = min(Double(width-4)/Double(trimmed.width), Double(height-4)/Double(trimmed.height))
    let w = fitExactly ? Double(width-4) : Double(trimmed.width)*scale
    let h = fitExactly ? Double(height-4) : Double(trimmed.height)*scale
    context.draw(trimmed, in: CGRect(x: (Double(width)-w)/2, y: (Double(height)-h)/2, width: w, height: h))
    let destination = CGImageDestinationCreateWithURL(output.appendingPathComponent(name) as CFURL, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(destination, context.makeImage()!, nil)
    precondition(CGImageDestinationFinalize(destination))
}
let huiBounds = bounds(load("Hui.png"))
let wordHeight = Int((140*huiBounds.height/huiBounds.width).rounded())
// Alpha-component bounds of each complete u body in the original artwork
// (alpha > 16). Exclude the separate macron, neighbouring letters and leaves.
// Match both dimensions: the original u shapes have different proportions.
let uBodyBounds: [String: CGRect] = [
    "Hui": CGRect(x: 974, y: 242, width: 544, height: 450),
    "Pu": CGRect(x: 1149, y: 243, width: 472, height: 409)
]
let referenceU = uBodyBounds["Hui"]!
let referenceScale = CGFloat(wordHeight) / huiBounds.height
for name in ["Hui", "Pu"] {
    let image = load(name+".png"), crop = bounds(load(name+".png"))
    let u = uBodyBounds[name]!
    let scaleX = referenceScale * referenceU.width / u.width
    let scaleY = referenceScale * referenceU.height / u.height
    save(image, crop: crop, width: Int((crop.width*scaleX).rounded())+4,
         height: Int(ceil(crop.height*scaleY))+4, name: name+".png", fitExactly: true)
}
for name in ["skull", "hei matai"] {
    let image = load(name+".png")
    save(image, crop: bounds(image), width: 176, height: 176, name: name+".png")
}
let frames = (1...5).map { load(String(format: "Clusters_Playing_Leaves_Assets/playing_leaf_%02d.png", $0)) }
// Every frame uses one shared square around the original center. The stationary
// leaves therefore keep identical positions despite the moving empty slot.
var radius: CGFloat = 0
for image in frames {
    let b = bounds(image), cx = CGFloat(image.width)/2, cy = CGFloat(image.height)/2
    radius = max(radius, max(max(cx-b.minX, b.maxX-cx), max(cy-b.minY, b.maxY-cy)))
}
for (index, image) in frames.enumerated() {
    let crop = CGRect(x: CGFloat(image.width)/2-radius, y: CGFloat(image.height)/2-radius,
                      width: radius*2, height: radius*2)
    save(image, crop: crop, width: 176, height: 176, name: String(format: "playing_leaf_%02d.png", index+1))
}
