# iOS Dev 앱 연동 계약 v1

기존 Xcode 프로젝트는 이 저장소에 없으며 수정하지 않습니다. `examples/PrismNotificationCoordinator.swift`는 통합용 예제이며 실제 iOS 빌드·기기 테스트를 완료한 코드가 아닙니다. 앱 담당자가 기존 Scene/알림 delegate/화면 coordinator에 연결해야 합니다.

## 앱 전달 파일

```bash
python -m prism.export_ios --profiles results/personalization.csv --predictions results/predictions.csv --user-key '<허용된 가명키>' --demo-id demo01 --reference-date YYYY-MM-DD --expires-at '<시간대 포함 만료시각>' --output results/prism_demo.json
```

하나의 모델과 관찰 기간을 선택한 predictions 파일을 사용합니다. user_key/reference_date에 대응하는 예측이 정확히 1개여야 합니다. 내보낸 JSON에는 원본/가명 user_key, device_key, 토큰, 실사용자 연결표를 포함하지 않고 테스트용 demoUserID를 사용합니다. 실제 앱 계정과의 연결은 앱 담당자가 허용된 테스트 계정에만 별도로 수행합니다.

필드: schemaVersion=1, demoUserID, referenceDate(KST), expiresAt(시간대 포함 ISO8601), timezone=Asia/Seoul, churnProbability[0,1], threshold[0,1], isRisk, target=observed_activity_proxy_7d, schedules.

schedule: weekdayKST(월0~일6), bandStartHour, bandHours, notifyHour, notifyDayOffset, body, route. 예: 월요일 21~24시 선호면 weekdayKST=0, notifyHour=0, notifyDayOffset=1, 즉 화요일 00시 후보입니다. 앱은 referenceDate보다 과거가 아니고 expiresAt 이전인 다음 실제 날짜를 계산합니다. UI의 Calendar weekday(일1~토7)로 변환 시 `(weekdayKST+1)%7+1`을 사용합니다.

논리 route: diary_write / vocabulary_review / pronunciation. 이는 기존 URL scheme이 아닙니다. 앱의 실제 화면 coordinator에 대응시킨 뒤 지원 여부를 확인합니다. 알림 클릭 delegate에서 허용된 route만 처리하고 기존 Amplitude 클릭 로깅 API로 연결합니다. 이 저장소에는 실제 앱 API 구현 근거가 없으므로 자동 호출하지 않습니다.

## 예약과 취소

1. 앱에서 알림 권한과 사용자 수신 동의를 확인합니다. 사용자 동의 요청 UI는 앱 담당 영역입니다.
2. JSON 만료, 위험 여부, 최신 계정, 해당 예상 이용 구간의 foreground 기록을 확인합니다. 과거 로그의 기록 부재로 최신 접속 상태를 추정하지 않습니다.
3. 예상 이용 구간 종료 시각을 1회성 로컬 알림 후보로 사용합니다. 식별자는 `prism.{demoUserID}.{실제예약KST날짜}`로 고정하여 같은 사용자·한국 날짜에 최대 1개 대기 요청만 둡니다.
4. 앱 활성화 시 오늘의 대기 알림을 취소하고 foreground 이력을 영속 저장합니다. 자정을 넘는 구간에서는 다음 날 후보 ID도 함께 취소합니다. 앱 재실행 후에도 같은 날짜에 재예약되지 않도록 이 영속 이력을 조회합니다.
5. 이미 발송된 날짜도 UserDefaults 등의 기록으로 보존하여 이후 재예약하지 않습니다. 예제는 UserDefaults에 차단 날짜와 예약 시각을 보존합니다. 앱 계정 전환과 만료 처리까지 연결하고 실제 기기에서 재실행·중복 방지를 검증해야 합니다.
6. 권한 거부/동의 철회/계정 전환/위험 해제/만료 시 관련 대기 요청을 취소합니다. 예약 성공이 정확한 표시 시각이나 실제 수신을 보장하지는 않습니다.

로컬 알림은 앱이 실행돼 예약할 때의 상태를 사용합니다. 서버처럼 발송 직전 최신 상태를 원격 확인할 수 없습니다. 기기에 JSON을 넣기만 하면 자동 예약되는 구조가 아니며 앱에서 새 후보 계산·권한·활동 확인을 호출해야 합니다.

검증 시나리오: 권한 허용/거부, 같은 날짜 반복 예약, 앱 접속 후 취소, 앱 프로세스 재실행, 계정 전환, 21~24시 자정 경계, JSON 만료, 알림 클릭 후 실제 화면 이동, 클릭 이벤트 적재. iOS SDK/권한/배포 대상은 실제 저장소에서 확인합니다.
