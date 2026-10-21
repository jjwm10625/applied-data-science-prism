// Integration example only. This file is not installed in the HiLingual Xcode project.
import Foundation
import UserNotifications

struct PrismNotice {
    let demoUserID: String
    let date: Date                 // Exact next candidate in Asia/Seoul; no repeats.
    let body: String
    let route: String
    let isRisk: Bool
    let expiresAt: Date
}

@available(iOS 15.0, macOS 12.0, *)
actor PrismNotificationCoordinator {
    private let center = UNUserNotificationCenter.current()
    private let storage = UserDefaults.standard
    private let blockedKey = "prism.blockedDates.v1"
    private let reservedKey = "prism.reservedDates.v1"
    private func blocked() -> Set<String> {
        Set(storage.stringArray(forKey: blockedKey) ?? [])
    }
    private func block(_ id: String) {
        var values = blocked(); values.insert(id)
        storage.set(Array(values), forKey: blockedKey)
    }
    private func reserve(_ id: String, date: Date) {
        var values = storage.dictionary(forKey: reservedKey) ?? [:]
        values[id] = date.timeIntervalSince1970
        storage.set(values, forKey: reservedKey)
    }
    private func alreadyElapsed(_ id: String) -> Bool {
        guard let stamp = (storage.dictionary(forKey: reservedKey) ?? [:])[id] as? Double else { return false }
        return stamp <= Date().timeIntervalSince1970
    }
    private let routes = Set(["diary_write", "vocabulary_review", "pronunciation"])
    private func day(_ date: Date) -> String {
        let f = DateFormatter()
        f.calendar = Calendar(identifier: .gregorian)
        f.timeZone = TimeZone(identifier: "Asia/Seoul")!
        f.dateFormat = "yyyy-MM-dd"
        return f.string(from: date)
    }
    private func identifier(_ user: String, _ date: Date) -> String {
        "prism.\(user).\(day(date))"
    }
    func schedule(_ notice: PrismNotice, hasActivityInExpectedBand: Bool, hasConsent: Bool) async throws {
        let id = identifier(notice.demoUserID, notice.date)
        let key = id
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .authorized || settings.authorizationStatus == .provisional,
              hasConsent, notice.isRisk, notice.date > Date(), notice.date < notice.expiresAt,
              !hasActivityInExpectedBand, !blocked().contains(key), !alreadyElapsed(key), routes.contains(notice.route) else {
            center.removePendingNotificationRequests(withIdentifiers: [id])
            return
        }
        // Same user + KST day always has the same identifier: repeated adds replace the request.
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Asia/Seoul")!
        var parts = calendar.dateComponents([.year,.month,.day,.hour,.minute], from: notice.date)
        parts.timeZone = calendar.timeZone
        let content = UNMutableNotificationContent()
        content.title = "HiLingual"
        content.body = notice.body
        content.userInfo = ["prism_route": notice.route]
        let trigger = UNCalendarNotificationTrigger(dateMatching: parts, repeats: false)
        reserve(id, date: notice.date)
        try await center.add(UNNotificationRequest(identifier: id, content: content, trigger: trigger))
        // Actor reentrancy: foreground cancellation may have happened while add was awaiting.
        if blocked().contains(key) {
            center.removePendingNotificationRequests(withIdentifiers: [id])
        }
    }
    func cancelOnForeground(demoUserID: String, date: Date = Date()) {
        let id = identifier(demoUserID, date)
        block(id)
        center.removePendingNotificationRequests(withIdentifiers: [id])
        center.removeDeliveredNotifications(withIdentifiers: [id])
    }
    func cancelCandidateOnForeground(demoUserID: String, candidateDate: Date) {
        // For a 21-24h band, caller passes the next day's 00:00 candidate too.
        let id = identifier(demoUserID, candidateDate)
        block(id)
        center.removePendingNotificationRequests(withIdentifiers: [id])
    }
    func route(from response: UNNotificationResponse) -> String? {
        guard let value = response.notification.request.content.userInfo["prism_route"] as? String,
              routes.contains(value) else { return nil }
        return value // Map to the app's existing coordinator; do not invent an existing URL scheme.
    }
}
