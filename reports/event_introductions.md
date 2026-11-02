# 이벤트 최초 관측일 (KST)

원본 분석 필터: 2025-10-08~2026-10-26. UUID 중복 제거 후 집계. 현재 전처리 파일은 변경하지 않음.
유효 원본 이벤트의 실제 관측 시작일: 2025-10-26. 이 날짜의 이벤트는 초기 관측 목록으로 분류.
날짜는 제공된 원본에서 처음 관측한 날짜이며 기능 출시일·앱 배포일을 확정하지 않음. 이름 변경·오탈자도 별도 이벤트로 표시.
원본 최초 날짜에는 현재 제외한 이상 ID의 로그도 포함. CSV의 first_retained_kst는 현재 정제 데이터에서 처음 남아 있는 시각.
앱 버전은 최초 관측일에 해당 이벤트를 기록한 버전 목록으로, 기능이 도입된 버전을 뜻하지 않음.

한국어 설명은 이벤트 이름을 해석한 것으로, 수집 명세로 확정한 정의가 아님.

## 2025-10-26 (관측 시작 시 이미 존재) (7개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `[Amplitude] Screen Viewed` | 화면 조회 기록 | 1.0.0 |
| `session_end` | 세션 종료 기록(실제 사용자 조작을 뜻하지 않을 수 있음) | 1.0.0 |
| `session_start` | 세션 시작 기록(실제 사용자 조작을 뜻하지 않을 수 있음) | 1.0.0 |
| `write_diary.click_back_diary` | 일기 작성 화면: 뒤로가기 클릭 | 1.0.0 |
| `write_diary.click_modal` | 일기 작성 화면: 팝업 관련 클릭(대상 확인 필요) | 1.0.0 |
| `write_diary.click_scan_text` | 일기 작성 화면: 텍스트 스캔 클릭 | 1.0.0 |
| `write_diary.pageview` | 일기 작성 화면: 화면 조회 | 1.0.0 |

## 2025-10-27 (14개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `bookmark_action` | 북마크 관련 동작(추가·해제 구분은 속성 확인 필요) | 1.0.0 |
| `click_back_diary` | 일기 화면의 뒤로가기 클릭 | 1.0.0 |
| `click_back_feedback` | 피드백 화면의 뒤로가기 클릭 | 1.0.0 |
| `click_dropdown` | 드롭다운 메뉴 클릭 | 1.0.0 |
| `click_empathy_action` | 공감 관련 버튼 클릭 | 1.0.0 |
| `click_feedback_toggle` | 피드백 표시 전환 클릭 | 1.0.0 |
| `click_modal` | 팝업 관련 클릭(대상 확인 필요) | 1.0.0 |
| `click_scan_text` | 텍스트 스캔 기능 클릭 | 1.0.0 |
| `pageview` | 페이지 조회 | 1.0.0 |
| `refresh_triggered` | 새로고침 발생 | 1.0.0 |
| `submitted_entry_diary` | 일기 입력 제출 | 1.0.0 |
| `submitted_post_diary` | 일기 게시 제출 | 1.0.0 |
| `toast_action` | 짧게 뜨는 안내 메시지 관련 동작(발생 조건 확인 필요) | 1.0.0 |
| `viewe_profile_user` | 사용자 프로필 조회로 추정(viewe 철자 확인 필요) | 1.0.0 |

## 2025-10-28 (9개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feed.refresh` | 피드 화면: 새로고침 클릭 | 1.0.1 |
| `click_home.profile` | 홈 화면: 프로필 클릭 | 1.0.1 |
| `click_vocabulary.voca_lookup` | 단어장 화면: 단어 찾아보기 클릭 | 1.0.1 |
| `view_feed.refresh` | 피드 새로고침 관련 조회 기록 | 1.0.1 |
| `view_feed.view_profile_user` | 피드에서 사용자 프로필 조회 | 1.0.1 |
| `view_home.page` | 홈 화면: 화면 조회 | 1.0.1 |
| `view_my_feed.page` | 내 피드 화면: 화면 조회 | 1.0.1 |
| `view_posted_diary.page` | 게시된 일기 화면: 화면 조회 | 1.0.1 |
| `view_vocabulary.page` | 단어장 화면: 화면 조회 | 1.0.1 |

## 2025-11-01 (5개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_home.diary_write` | 홈 화면: 일기 쓰기 클릭 | 1.0.1 |
| `click_write_diary.submit_cta` | 일기 작성 화면의 제출 버튼 클릭 | 1.0.1 |
| `click_write_diary.textfield` | 일기 작성 화면: 텍스트 입력란 클릭 | 1.0.1 |
| `view_feedback.page` | 피드백 화면: 화면 조회 | 1.0.1 |
| `view_write_diary.page` | 일기 작성 화면: 화면 조회 | 1.0.1 |

## 2025-11-05 (2개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.bookmark_action` | 피드백 화면: 북마크 관련 클릭 | 1.0.2 |
| `view_home.opend_diary_view` | 홈에서 일기 열기·조회로 추정(opend 철자 확인 필요) | 1.0.2 |

## 2025-11-06 (6개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.submitted_post_diary` | 피드백 화면에서 일기 게시 제출 관련 클릭 | 1.0.2 |
| `click_feedback.toast_action` | 피드백 화면: 짧게 뜨는 안내 메시지 관련 클릭 | 1.0.2 |
| `click_write_diary.back_diary` | 일기 작성 화면: 뒤로가기 클릭 | 1.0.2 |
| `click_write_diary.dropdown` | 일기 작성 화면: 드롭다운 클릭 | 1.0.2 |
| `click_write_diary.modal` | 일기 작성 화면: 팝업 관련 클릭(대상 확인 필요) | 1.0.2 |
| `click_write_diary.scan_text` | 일기 작성 화면: 텍스트 스캔 클릭 | 1.0.2 |

## 2025-11-11 (2개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.back_feedback` | 피드백 화면의 뒤로가기 관련 클릭(이동 대상 확인 필요) | 1.0.2 |
| `click_home.more_menu` | 홈 화면: 더보기 메뉴 클릭 | 1.0.2 |

## 2025-11-13 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.toggle` | 피드백 화면: 표시 전환 클릭(전환 대상 확인 필요) | 1.0.2 |

## 2025-11-18 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_home.switch_language` | 홈 화면: 언어 전환 클릭 | 1.0.2 |

## 2025-11-27 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_vocabulary.voca_sort_changed` | 단어장 화면: 단어 정렬 변경 | 1.1.1 |

## 2025-12-13 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feed.empathy_action` | 피드 화면: 공감 관련 클릭 | 1.1.1 |

## 2026-05-24 (3개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_diary_pronunciation_btn` | 일기 발음 버튼 클릭 | 2.2.0 |
| `click_vocab_pronunciation_btn` | 단어 발음 버튼 클릭 | 2.2.0 |
| `click_vocab_review_btn` | 단어 복습 버튼 클릭 | 2.2.0 |

## 2026-06-27 (5개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_home.network_error_retry` | 홈 화면: 네트워크 오류 후 재시도 클릭 | 2.2.0 |
| `click_home.server_error_retry` | 홈 화면: 서버 오류 후 재시도 클릭 | 2.2.0 |
| `click_mypage.network_error_retry` | 마이페이지 화면: 네트워크 오류 후 재시도 클릭 | 2.2.0 |
| `click_vocabulary.network_error_retry` | 단어장 화면: 네트워크 오류 후 재시도 클릭 | 2.2.0 |
| `view_profile_user` | 사용자 프로필 조회 | 2.2.0 |

## 2026-06-28 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_home.data_not_found_go_back` | 홈 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.2.0 |

## 2026-07-03 (3개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feed.network_error_retry` | 피드 화면: 네트워크 오류 후 재시도 클릭 | 2.3.2 |
| `click_user_profile.server_error_go_back` | 사용자 프로필 화면: 서버 오류 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_user_profile.server_error_retry` | 사용자 프로필 화면: 서버 오류 후 재시도 클릭 | 2.3.2 |

## 2026-07-04 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_ai_feedback.feedback_retry` | AI 피드백 화면: 피드백 재시도 클릭 | 2.3.2 |

## 2026-07-06 (9개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feed.data_not_found_go_back` | 피드 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_feed.server_error_retry` | 피드 화면: 서버 오류 후 재시도 클릭 | 2.3.2 |
| `click_feedback.server_error_go_back` | 피드백 화면: 서버 오류 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_my_feed.data_not_found_go_back` | 내 피드 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_mypage.data_not_found_go_back` | 마이페이지 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_mypage.server_error_retry` | 마이페이지 화면: 서버 오류 후 재시도 클릭 | 2.3.2 |
| `click_posted_diary.data_not_found_go_back` | 게시된 일기 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_vocabulary.data_not_found_go_back` | 단어장 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.3.2 |
| `click_vocabulary.server_error_retry` | 단어장 화면: 서버 오류 후 재시도 클릭 | 2.3.2 |

## 2026-07-14 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_user_profile.data_not_found_go_back` | 사용자 프로필 화면: 데이터 없음 안내에서 뒤로가기 클릭 | 2.3.1 |

## 2026-08-01 (2개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feed.profile_view` | 피드 화면: 프로필 보기 클릭 | 2.3.2 |
| `view_page` | 화면 조회(구체적인 화면은 이벤트 속성 확인 필요) | 2.3.2 |

## 2026-08-04 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_toast_action` | 짧게 뜨는 안내 메시지 관련 클릭 | 2.5.1 |

## 2026-08-05 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_bookmark_action` | 북마크 관련 버튼 클릭 | 2.5.1 |

## 2026-08-06 (8개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.post_diary` | 피드백 화면: 일기 게시 클릭 | 2.4.1 |
| `click_home.diary_view` | 홈 화면: 일기 보기 클릭 | 2.4.1 |
| `click_home.streak_revive` | 홈에서 연속 학습 기록 복구 클릭 | 2.4.1 |
| `click_onboarding.skip` | 온보딩(초기 사용 안내) 화면: 안내 건너뛰기 클릭 | 2.4.2 |
| `click_posted_diary.toggle` | 게시된 일기 화면: 표시 전환 클릭(전환 대상 확인 필요) | 2.4.1 |
| `click_vocab_pronunciation_btn_play` | 단어 발음 재생 버튼 클릭 | 2.4.1 |
| `click_write_diary.submit_entry` | 일기 작성 화면에서 입력 제출 클릭 | 2.4.1 |
| `view_ad_action` | 광고 조회 관련 기록(노출·시청 완료 구분은 확인 필요) | 2.4.1 |

## 2026-08-09 (7개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_back` | 뒤로가기 클릭 | 2.4.2, 2.5.1 |
| `click_diary_pronunciation_btn_play` | 일기 발음 재생 버튼 클릭 | 2.5.1 |
| `click_feedback_loading.server_error_retry` | 피드백 로딩 화면: 서버 오류 후 재시도 클릭 | 2.4.2 |
| `click_onborading.skip` | 온보딩(원본 이름 onborading 오탈자 추정) 화면: 안내 건너뛰기 클릭 | 2.5.1 |
| `click_push_notification` | 푸시 알림 클릭 | 2.5.1 |
| `click_user_profile.follow` | 사용자 프로필 화면: 팔로우 클릭 | 2.5.1 |
| `click_vocabulary.sort_changed` | 단어장 화면: 정렬 변경 | 2.5.1 |

## 2026-08-14 (3개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_vocabulary.empty_data_confirm` | 단어장 화면: 빈 데이터 안내 확인 클릭 | 2.5.1 |
| `click_vocabulary.review_btn` | 단어장 화면: 복습 버튼 클릭 | 2.4.2, 2.4.3 |
| `click_vocabulary.server_error_confirm` | 단어장 화면: 서버 오류 안내 확인 클릭 | 2.5.1 |

## 2026-08-15 (3개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.empty_data_confirm` | 피드백 화면: 빈 데이터 안내 확인 클릭 | 2.7.0 |
| `click_onboarding.server_error_confirm` | 온보딩(초기 사용 안내) 화면: 서버 오류 안내 확인 클릭 | 2.4.1 |
| `click_write_diary.back_modal` | 일기 작성 화면: 뒤로가기 팝업 관련 클릭(정확한 동작 확인 필요) | 2.7.0 |

## 2026-08-17 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_notification.profile_view` | 앱 내 알림 화면: 프로필 보기 클릭 | 2.5.0 |

## 2026-08-19 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_user_profile.server_error_confirm` | 사용자 프로필 화면: 서버 오류 안내 확인 클릭 | 2.7.0 |

## 2026-08-20 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_user_profile.profile_view` | 사용자 프로필 화면의 프로필 보기 관련 클릭(대상 확인 필요) | 2.5.0 |

## 2026-08-25 (2개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_widget` | 위젯 클릭 | 2.5.1 |
| `widget_count` | 위젯 카운트 기록(정확한 측정 대상·발생 조건 확인 필요) | 2.5.1 |

## 2026-08-27 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_vocabulary.unknown_filter` | 단어장에서 미학습·모르는 단어 필터로 추정(정의 확인 필요) | 2.5.1, 2.5.2 |

## 2026-09-06 (2개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_my_feed.server_error_confirm` | 내 피드 화면: 서버 오류 안내 확인 클릭 | 2.7.2 |
| `click_posted_diary.server_error_go_back` | 게시된 일기 화면: 서버 오류 안내에서 뒤로가기 클릭 | 2.7.2 |

## 2026-10-01 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feed.server_error_confirm` | 피드 화면: 서버 오류 안내 확인 클릭 | 2.7.2 |

## 2026-10-15 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_feedback.network_error_retry` | 피드백 화면: 네트워크 오류 후 재시도 클릭 | 2.7.2 |

## 2026-10-19 (1개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_my_feed.server_error_go_back` | 내 피드 화면: 서버 오류 안내에서 뒤로가기 클릭 | 2.7.2 |

## 2026-10-25 (2개)

| 이벤트 | 한국어 설명 | 최초 관측일 앱 버전 |
|---|---|---|
| `click_write_diary.network_error_go_back` | 일기 작성 화면: 네트워크 오류 안내에서 뒤로가기 클릭 | 2.7.2 |
| `click_write_diary.network_error_retry` | 일기 작성 화면: 네트워크 오류 후 재시도 클릭 | 2.7.2 |

