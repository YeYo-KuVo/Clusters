import Foundation
import AVFoundation

final class SoundEngine: NSObject, AVAudioPlayerDelegate {
    let root: URL
    var library: [String: [URL]] = [:]
    var previous: [String: URL] = [:]
    var players: [String: AVAudioPlayer] = [:]
    var buttons: [AVAudioPlayer] = []
    var timers: [String: Timer] = [:]
    var ambient = false
    let levels: [String: Float] = ["BIRDS": 0.28, "PERCUSION": 0.16, "WATER": 0.25]

    init(root: URL) {
        self.root = root
        super.init()
        let extensions = Set(["wav", "mp3", "m4a", "aif", "aiff", "flac", "ogg", "caf"])
        for category in ["BUTTON", "BIRDS", "PERCUSION", "WATER"] {
            let files = (try? FileManager.default.contentsOfDirectory(
                at: root.appendingPathComponent(category), includingPropertiesForKeys: nil)) ?? []
            // Prefer WAV when the same recording also exists as MP3.
            var unique: [String: URL] = [:]
            for file in files.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) {
                guard extensions.contains(file.pathExtension.lowercased()) else { continue }
                let key = file.deletingPathExtension().lastPathComponent
                if unique[key] == nil || file.pathExtension.lowercased() == "wav" { unique[key] = file }
            }
            library[category] = unique.values.sorted { $0.lastPathComponent < $1.lastPathComponent }
        }
    }

    func makePlayer(_ category: String) -> AVAudioPlayer? {
        let all = library[category] ?? []
        var candidates = all.filter { all.count == 1 || $0 != previous[category] }.shuffled()
        if candidates.isEmpty { candidates = all }
        for file in candidates {
            do {
                let player = try AVAudioPlayer(contentsOf: file)
                player.prepareToPlay()
                previous[category] = file
                return player
            } catch {
                // Unsupported/corrupt files cannot prevent other recordings playing.
                fputs("Skipping audio file: \(file.lastPathComponent): \(error)\n", stderr)
            }
        }
        return nil
    }

    func button() {
        buttons.removeAll { !$0.isPlaying }
        guard let player = makePlayer("BUTTON") else { return }
        player.volume = 0.5
        player.delegate = self
        buttons.append(player)
        player.play()
    }

    func chirp(_ path: String) {
        guard let player = try? AVAudioPlayer(contentsOf: URL(fileURLWithPath: path)) else { return }
        // Keep just one bird sound active, including the completion cue.
        timers["BIRDS"]?.invalidate()
        players["BIRDS"]?.stop()
        players["BIRDS"] = player
        player.delegate = self
        player.volume = 0.35
        player.play()
    }

    func schedule(_ category: String, initial: Bool = false) {
        guard ambient else { return }
        timers[category]?.invalidate()
        let delay: Double
        if category == "WATER" { delay = initial ? 0 : 0.05 }
        else if category == "BIRDS" { delay = Double.random(in: initial ? 3...10 : 12...30) }
        else { delay = Double.random(in: initial ? 8...18 : 18...40) }
        timers[category] = Timer.scheduledTimer(withTimeInterval: max(0.01, delay), repeats: false) {
            [weak self] _ in self?.playAmbient(category)
        }
    }

    func playAmbient(_ category: String) {
        guard ambient, players[category] == nil else { return }
        guard let player = makePlayer(category) else {
            // Retry later if files are temporarily unavailable.
            timers[category] = Timer.scheduledTimer(withTimeInterval: 30, repeats: false) {
                [weak self] _ in self?.playAmbient(category)
            }
            return
        }
        player.delegate = self
        player.volume = category == "WATER" ? 0 : (levels[category] ?? 0.2)
        players[category] = player
        player.play()
    }

    func start() {
        guard !ambient else { return }
        ambient = true
        for category in ["WATER", "BIRDS", "PERCUSION"] { schedule(category, initial: true) }
        timers["fade"] = Timer.scheduledTimer(withTimeInterval: 0.04, repeats: true) { [weak self] _ in
            guard let self = self, let water = self.players["WATER"] else { return }
            let fade = min(3.0, water.duration / 3)
            guard fade > 0 else { return }
            let envelope = max(0, min(1, min(water.currentTime / fade,
                                            (water.duration - water.currentTime) / fade)))
            water.volume = Float(envelope) * (self.levels["WATER"] ?? 0.25)
        }
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        if let category = players.first(where: { $0.value === player })?.key {
            players.removeValue(forKey: category)
            schedule(category)
        }
        buttons.removeAll { $0 === player }
    }

    func stop() {
        ambient = false
        timers.values.forEach { $0.invalidate() }
        timers.removeAll()
        players.values.forEach { $0.stop() }
        players.removeAll()
        buttons.forEach { $0.stop() }
        buttons.removeAll()
    }
}

let arguments = CommandLine.arguments
if arguments.count < 2 { exit(1) }
let engine = SoundEngine(root: URL(fileURLWithPath: arguments[1]))
// Decode every supplied file without playing anything when validating the library.
if arguments.contains("--validate") {
    var failures = 0
    for category in ["BUTTON", "BIRDS", "PERCUSION", "WATER"] {
        let files = engine.library[category] ?? []
        print("\(category): \(files.count) recordings")
        for file in files {
            do {
                let player = try AVAudioPlayer(contentsOf: file)
                print("  OK \(String(format: "%.2f", player.duration))s \(file.lastPathComponent)")
            } catch { failures += 1; print("  UNSUPPORTED \(file.lastPathComponent): \(error)") }
        }
    }
    exit(failures == 0 ? 0 : 2)
}
DispatchQueue.global().async {
    while let line = readLine() {
        DispatchQueue.main.async {
            switch line {
            case "button": engine.button()
            case "chirp": if arguments.count > 2 { engine.chirp(arguments[2]) }
            case "start": engine.start()
            case "stop": engine.stop()
            case "quit": engine.stop(); exit(0)
            default: break
            }
        }
    }
    DispatchQueue.main.async { engine.stop(); exit(0) }
}
RunLoop.main.run()
