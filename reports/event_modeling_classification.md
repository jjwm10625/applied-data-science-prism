# 모델링용 이벤트 분류 검토안

110개 이벤트 전부 포함. 기존 전처리 CSV/Parquet와 코드는 변경하지 않음.
분류는 이름과 관측 로그에 근거한 후보이며, 출시·수집 명세로 확정한 매핑이 아님.
공통 행동 후보도 전체 기간에서 수집되었다는 의미가 아님. 수집 가능 여부는 모든 행동에 별도로 적용.
추가 기능·유입은 버전별 사용 가능 여부를 우선 확인할 후보이며 신규 기능 출시를 확정하지 않음.
같은 의미 후보라도 단순 합산 금지: 사용자·세션·시각·대상 ID·발행 순서를 대조해 중복과 시도/완료 구분.
기준일 피처에는 기준일 이전에 관측한 버전/행동만 사용. 미래 버전으로 과거 사용 가능 여부를 채우지 않음.
지원 전/수집 불명확은 0과 구분. available과 tracking_available 또는 unknown 상태를 별도로 관리.
28일 창 중 사용 가능 기간이 짧으면 eligible_days를 함께 기록하고 검증된 사용 가능 일수 기준 사용률을 고려.
활동·recency·라벨은 같은 활동 정의를 사용. 앱 방문 이탈인지 학습 중단인지 먼저 구분. 실제 푸시/위젯 클릭은 방문 근거 후보지만 학습 완료는 아님.
신규 이벤트는 자동으로 활동 인정하지 않고 검토 목록에 추가. 이 문서는 적용을 위한 기준 제안이며 현재 라벨은 변경하지 않음.

## 화면 조회 (14개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `[Amplitude] Screen Viewed` | 화면 조회 기록 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `write_diary.pageview` | 일기 작성 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `pageview` | 페이지 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `viewe_profile_user` | 사용자 프로필 조회로 추정(viewe 철자 확인 필요) | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_feed.view_profile_user` | 피드에서 사용자 프로필 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_home.page` | 홈 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_my_feed.page` | 내 피드 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_posted_diary.page` | 게시된 일기 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_vocabulary.page` | 단어장 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_feedback.page` | 피드백 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_write_diary.page` | 일기 작성 화면: 화면 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_home.opend_diary_view` | 홈에서 일기 열기·조회로 추정(opend 철자 확인 필요) | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_profile_user` | 사용자 프로필 조회 | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |
| `view_page` | 화면 조회(구체적인 화면은 이벤트 속성 확인 필요) | `screen_view` | 전경 화면의 실제 조회임을 확인한 경우 인정 |

## 자동·시스템 (3개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `session_end` | 세션 종료 기록(실제 사용자 조작을 뜻하지 않을 수 있음) | `session_end` | 단독으로 활동 인정하지 않음 |
| `session_start` | 세션 시작 기록(실제 사용자 조작을 뜻하지 않을 수 있음) | `session_start` | 단독으로 활동 인정하지 않음 |
| `widget_count` | 위젯 카운트 기록(정확한 측정 대상·발생 조건 확인 필요) | `widget_count` | 단독으로 활동 인정하지 않음 |

## 화면 조작·이동 (21개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `write_diary.click_back_diary` | 일기 작성 화면: 뒤로가기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_back_diary` | 일기 화면의 뒤로가기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_back_feedback` | 피드백 화면의 뒤로가기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_dropdown` | 드롭다운 메뉴 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_feedback_toggle` | 피드백 표시 전환 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_feed.refresh` | 피드 화면: 새로고침 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_home.profile` | 홈 화면: 프로필 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_write_diary.back_diary` | 일기 작성 화면: 뒤로가기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_write_diary.dropdown` | 일기 작성 화면: 드롭다운 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_feedback.back_feedback` | 피드백 화면의 뒤로가기 관련 클릭(이동 대상 확인 필요) | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_home.more_menu` | 홈 화면: 더보기 메뉴 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_feedback.toggle` | 피드백 화면: 표시 전환 클릭(전환 대상 확인 필요) | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_home.switch_language` | 홈 화면: 언어 전환 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_vocabulary.voca_sort_changed` | 단어장 화면: 단어 정렬 변경 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_feed.profile_view` | 피드 화면: 프로필 보기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_onboarding.skip` | 온보딩(초기 사용 안내) 화면: 안내 건너뛰기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_posted_diary.toggle` | 게시된 일기 화면: 표시 전환 클릭(전환 대상 확인 필요) | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_back` | 뒤로가기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_onborading.skip` | 온보딩(원본 이름 onborading 오탈자 추정) 화면: 안내 건너뛰기 클릭 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_vocabulary.sort_changed` | 단어장 화면: 정렬 변경 | `ui_interaction` | 조건부 인정: 실제 클릭 |
| `click_user_profile.profile_view` | 사용자 프로필 화면의 프로필 보기 관련 클릭(대상 확인 필요) | `ui_interaction` | 조건부 인정: 실제 클릭 |

## 의미·발생 조건 확인 (10개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `write_diary.click_modal` | 일기 작성 화면: 팝업 관련 클릭(대상 확인 필요) | `write_diary.click_modal` | 확인 전 보류 |
| `click_modal` | 팝업 관련 클릭(대상 확인 필요) | `click_modal` | 확인 전 보류 |
| `refresh_triggered` | 새로고침 발생 | `refresh_triggered` | 확인 전 보류 |
| `toast_action` | 짧게 뜨는 안내 메시지 관련 동작(발생 조건 확인 필요) | `toast_action` | 확인 전 보류 |
| `view_feed.refresh` | 피드 새로고침 관련 조회 기록 | `view_feed.refresh` | 확인 전 보류 |
| `click_feedback.toast_action` | 피드백 화면: 짧게 뜨는 안내 메시지 관련 클릭 | `click_feedback.toast_action` | 확인 전 보류 |
| `click_write_diary.modal` | 일기 작성 화면: 팝업 관련 클릭(대상 확인 필요) | `click_write_diary.modal` | 확인 전 보류 |
| `click_toast_action` | 짧게 뜨는 안내 메시지 관련 클릭 | `click_toast_action` | 확인 전 보류 |
| `view_ad_action` | 광고 조회 관련 기록(노출·시청 완료 구분은 확인 필요) | `view_ad_action` | 확인 전 보류 |
| `click_write_diary.back_modal` | 일기 작성 화면: 뒤로가기 팝업 관련 클릭(정확한 동작 확인 필요) | `click_write_diary.back_modal` | 확인 전 보류 |

## 공통 행동 후보 (24개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `write_diary.click_scan_text` | 일기 작성 화면: 텍스트 스캔 클릭 | `diary_scan` | 조건부 인정: 사용자 행동 연결 확인 |
| `bookmark_action` | 북마크 관련 동작(추가·해제 구분은 속성 확인 필요) | `bookmark` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_empathy_action` | 공감 관련 버튼 클릭 | `empathy` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_scan_text` | 텍스트 스캔 기능 클릭 | `diary_scan` | 조건부 인정: 사용자 행동 연결 확인 |
| `submitted_entry_diary` | 일기 입력 제출 | `diary_submit_record` | 조건부 인정: 사용자 행동 연결 확인 |
| `submitted_post_diary` | 일기 게시 제출 | `diary_publish_record` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_vocabulary.voca_lookup` | 단어장 화면: 단어 찾아보기 클릭 | `vocabulary_lookup` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_home.diary_write` | 홈 화면: 일기 쓰기 클릭 | `diary_write_open` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_write_diary.submit_cta` | 일기 작성 화면의 제출 버튼 클릭 | `diary_submit_click` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_write_diary.textfield` | 일기 작성 화면: 텍스트 입력란 클릭 | `diary_text_input` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_feedback.bookmark_action` | 피드백 화면: 북마크 관련 클릭 | `bookmark` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_feedback.submitted_post_diary` | 피드백 화면에서 일기 게시 제출 관련 클릭 | `diary_publish_click` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_write_diary.scan_text` | 일기 작성 화면: 텍스트 스캔 클릭 | `diary_scan` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_feed.empathy_action` | 피드 화면: 공감 관련 클릭 | `empathy` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_diary_pronunciation_btn` | 일기 발음 버튼 클릭 | `diary_pronunciation` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_vocab_pronunciation_btn` | 단어 발음 버튼 클릭 | `vocabulary_pronunciation` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_vocab_review_btn` | 단어 복습 버튼 클릭 | `vocabulary_review` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_bookmark_action` | 북마크 관련 버튼 클릭 | `bookmark` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_feedback.post_diary` | 피드백 화면: 일기 게시 클릭 | `diary_publish_click` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_home.diary_view` | 홈 화면: 일기 보기 클릭 | `diary_read_click` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_vocab_pronunciation_btn_play` | 단어 발음 재생 버튼 클릭 | `vocabulary_pronunciation` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_write_diary.submit_entry` | 일기 작성 화면에서 입력 제출 클릭 | `diary_submit_click` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_diary_pronunciation_btn_play` | 일기 발음 재생 버튼 클릭 | `diary_pronunciation` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_vocabulary.review_btn` | 단어장 화면: 복습 버튼 클릭 | `vocabulary_review` | 조건부 인정: 사용자 행동 연결 확인 |

## 오류 대응 (32개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `click_home.network_error_retry` | 홈 화면: 네트워크 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_home.server_error_retry` | 홈 화면: 서버 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_mypage.network_error_retry` | 마이페이지 화면: 네트워크 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_vocabulary.network_error_retry` | 단어장 화면: 네트워크 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_home.data_not_found_go_back` | 홈 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feed.network_error_retry` | 피드 화면: 네트워크 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_user_profile.server_error_go_back` | 사용자 프로필 화면: 서버 오류 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_user_profile.server_error_retry` | 사용자 프로필 화면: 서버 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_ai_feedback.feedback_retry` | AI 피드백 화면: 피드백 재시도 클릭 | `feedback_retry` | 조건부 인정: 사용자 재시도 |
| `click_feed.data_not_found_go_back` | 피드 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feed.server_error_retry` | 피드 화면: 서버 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feedback.server_error_go_back` | 피드백 화면: 서버 오류 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_my_feed.data_not_found_go_back` | 내 피드 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_mypage.data_not_found_go_back` | 마이페이지 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_mypage.server_error_retry` | 마이페이지 화면: 서버 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_posted_diary.data_not_found_go_back` | 게시된 일기 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_vocabulary.data_not_found_go_back` | 단어장 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_vocabulary.server_error_retry` | 단어장 화면: 서버 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_user_profile.data_not_found_go_back` | 사용자 프로필 화면: 데이터 없음 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feedback_loading.server_error_retry` | 피드백 로딩 화면: 서버 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_vocabulary.empty_data_confirm` | 단어장 화면: 빈 데이터 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_vocabulary.server_error_confirm` | 단어장 화면: 서버 오류 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feedback.empty_data_confirm` | 피드백 화면: 빈 데이터 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_onboarding.server_error_confirm` | 온보딩(초기 사용 안내) 화면: 서버 오류 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_user_profile.server_error_confirm` | 사용자 프로필 화면: 서버 오류 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_my_feed.server_error_confirm` | 내 피드 화면: 서버 오류 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_posted_diary.server_error_go_back` | 게시된 일기 화면: 서버 오류 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feed.server_error_confirm` | 피드 화면: 서버 오류 안내 확인 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_feedback.network_error_retry` | 피드백 화면: 네트워크 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_my_feed.server_error_go_back` | 내 피드 화면: 서버 오류 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_write_diary.network_error_go_back` | 일기 작성 화면: 네트워크 오류 안내에서 뒤로가기 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |
| `click_write_diary.network_error_retry` | 일기 작성 화면: 네트워크 오류 후 재시도 클릭 | `error_response` | 조건부 인정: 명시적 사용자 클릭임을 확인 |

## 추가 기능·유입 (6개)

| 이벤트 | 한국어 설명 | 행동 그룹 후보 | 활동 판정 제안 |
|---|---|---|---|
| `click_home.streak_revive` | 홈에서 연속 학습 기록 복구 클릭 | `streak_revive` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_push_notification` | 푸시 알림 클릭 | `push_entry` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_user_profile.follow` | 사용자 프로필 화면: 팔로우 클릭 | `follow` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_notification.profile_view` | 앱 내 알림 화면: 프로필 보기 클릭 | `notification_profile_entry` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_widget` | 위젯 클릭 | `widget_entry` | 조건부 인정: 사용자 행동 연결 확인 |
| `click_vocabulary.unknown_filter` | 단어장에서 미학습·모르는 단어 필터로 추정(정의 확인 필요) | `vocabulary_unknown_filter` | 조건부 인정: 사용자 행동 연결 확인 |

