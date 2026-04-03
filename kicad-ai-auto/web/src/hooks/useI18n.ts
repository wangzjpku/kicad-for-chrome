/**
 * React hook for i18n (internationalization).
 *
 * Provides:
 * - t() function for string lookup
 * - Language switching
 * - Auto-detection from browser settings
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

export type Language = 'en-US' | 'zh-CN' | 'ja-JP';

const STORAGE_KEY = 'kicad-ai-lang';

// Fallback embedded translations (loaded instantly, before API call)
const FALLBACK: Record<Language, Record<string, string>> = {
  'en-US': {
    'app.title': 'KiCad AI Auto',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.delete': 'Delete',
    'common.close': 'Close',
    'common.loading': 'Loading...',
    'common.error': 'Error',
    'common.success': 'Success',
    'common.search': 'Search',
    'common.export': 'Export',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.finish': 'Finish',
    'auth.login': 'Login',
    'auth.register': 'Register',
    'auth.logout': 'Logout',
    'project.new': 'New Project',
    'project.save': 'Save Project',
    'pcb.title': 'PCB Editor',
    'pcb.route': 'Route',
    'pcb.run_drc': 'Run DRC',
    'drc.title': 'Design Rule Check',
    'drc.errors': 'Errors',
    'drc.warnings': 'Warnings',
    'mfg.title': 'Manufacturing',
    'ai.title': 'AI Assistant',
  },
  'zh-CN': {
    'app.title': 'KiCad AI Auto',
    'common.save': '保存',
    'common.cancel': '取消',
    'common.delete': '删除',
    'common.close': '关闭',
    'common.loading': '加载中...',
    'common.error': '错误',
    'common.success': '成功',
    'common.search': '搜索',
    'common.export': '导出',
    'common.back': '返回',
    'common.next': '下一步',
    'common.finish': '完成',
    'auth.login': '登录',
    'auth.register': '注册',
    'auth.logout': '退出',
    'project.new': '新建项目',
    'project.save': '保存项目',
    'pcb.title': 'PCB 编辑器',
    'pcb.route': '布线',
    'pcb.run_drc': '运行 DRC',
    'drc.title': '设计规则检查',
    'drc.errors': '错误',
    'drc.warnings': '警告',
    'mfg.title': '制造',
    'ai.title': 'AI 助手',
  },
  'ja-JP': {
    'app.title': 'KiCad AI Auto',
    'common.save': '保存',
    'common.cancel': 'キャンセル',
    'common.delete': '削除',
    'common.close': '閉じる',
    'common.loading': '読み込み中...',
    'common.error': 'エラー',
    'common.success': '成功',
    'common.search': '検索',
    'common.export': 'エクスポート',
    'common.back': '戻る',
    'common.next': '次へ',
    'common.finish': '完了',
    'auth.login': 'ログイン',
    'auth.register': '新規登録',
    'auth.logout': 'ログアウト',
    'project.new': '新規プロジェクト',
    'project.save': '保存',
    'pcb.title': 'PCBエディタ',
    'pcb.route': '配線',
    'pcb.run_drc': 'DRC実行',
    'drc.title': '設計ルールチェック',
    'drc.errors': 'エラー',
    'drc.warnings': '警告',
    'mfg.title': '製造',
    'ai.title': 'AIアシスタント',
  },
};

function detectBrowserLang(): Language {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && stored in FALLBACK) return stored as Language;

  const nav = navigator.language || 'en';
  if (nav.startsWith('zh')) return 'zh-CN';
  if (nav.startsWith('ja')) return 'ja-JP';
  return 'en-US';
}

export function useI18n() {
  const [lang, setLangState] = useState<Language>(detectBrowserLang);
  const [apiTranslations, setApiTranslations] = useState<Record<string, string>>({});

  // Load full translations from API
  useEffect(() => {
    fetch(`/api/v1/i18n/${lang}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.translations) {
          setApiTranslations(data.translations);
        }
      })
      .catch(() => {
        // Use fallback translations
      });
  }, [lang]);

  const translations = useMemo(() => {
    const base = FALLBACK[lang] || FALLBACK['en-US'];
    return { ...base, ...apiTranslations };
  }, [lang, apiTranslations]);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      let value = translations[key] || FALLBACK['en-US'][key] || key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          value = value.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        });
      }
      return value;
    },
    [translations],
  );

  const setLang = useCallback((newLang: Language) => {
    setLangState(newLang);
    localStorage.setItem(STORAGE_KEY, newLang);
    document.documentElement.lang = newLang;
  }, []);

  const languages = useMemo(
    () => [
      { code: 'en-US' as Language, name: 'English', native: 'English' },
      { code: 'zh-CN' as Language, name: 'Chinese (Simplified)', native: '简体中文' },
      { code: 'ja-JP' as Language, name: 'Japanese', native: '日本語' },
    ],
    [],
  );

  return { t, lang, setLang, languages };
}
