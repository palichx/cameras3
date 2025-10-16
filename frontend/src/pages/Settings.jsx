import { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const Settings = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings`);
      setSettings(response.data);
      setLoading(false);
    } catch (error) {
      toast.error('Ошибка загрузки настроек');
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/settings`, {
        performance_profile: settings.performance_profile,
        telegram_bot_token: settings.telegram_bot_token,
        telegram_chat_id: settings.telegram_chat_id,
        default_storage_path: settings.default_storage_path,
      });
      toast.success('Настройки сохранены');
    } catch (error) {
      toast.error('Ошибка сохранения настроек');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!settings) return null;

  const currentProfile = settings.profiles[settings.performance_profile];

  return (
    <div className="p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-[var(--text-primary)] mb-2">Глобальные настройки</h1>
        <p className="text-[var(--text-secondary)]">Настройка параметров системы</p>
      </div>

      <div className="max-w-3xl space-y-8">
        {/* Performance Profile */}
        <div className="glass p-6 rounded-2xl space-y-4">
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Профиль производительности</h2>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="w-4 h-4 text-[var(--text-secondary)]" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Выберите профиль в зависимости от мощности вашей системы. Это влияет на качество видео и нагрузку на CPU.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div>
            <Label>Выберите профиль</Label>
            <Select
              value={settings.performance_profile}
              onValueChange={(value) => setSettings({ ...settings, performance_profile: value })}
            >
              <SelectTrigger data-testid="performance-profile-select" className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-primary)]">
                {Object.entries(settings.profiles).map(([key, profile]) => (
                  <SelectItem key={key} value={key}>
                    {profile.name} - {profile.description}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {currentProfile && (
            <div className="bg-[var(--bg-tertiary)] p-4 rounded-lg space-y-2">
              <h3 className="font-semibold text-[var(--text-primary)] mb-3">Текущие параметры</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-[var(--text-secondary)]">Макс. разрешение:</span>
                  <span className="text-[var(--text-primary)] ml-2 font-medium">{currentProfile.max_resolution_width}px</span>
                </div>
                <div>
                  <span className="text-[var(--text-secondary)]">Целевой FPS:</span>
                  <span className="text-[var(--text-primary)] ml-2 font-medium">{currentProfile.target_fps}</span>
                </div>
                <div>
                  <span className="text-[var(--text-secondary)]">Качество JPEG:</span>
                  <span className="text-[var(--text-primary)] ml-2 font-medium">{currentProfile.jpeg_quality}%</span>
                </div>
                <div>
                  <span className="text-[var(--text-secondary)]">Интервал проверки:</span>
                  <span className="text-[var(--text-primary)] ml-2 font-medium">{currentProfile.motion_check_interval}s</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <Separator className="bg-[var(--border)]" />

        {/* Telegram Settings */}
        <div className="glass p-6 rounded-2xl space-y-4">
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">Настройки Telegram</h2>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="w-4 h-4 text-[var(--text-secondary)]" />
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Для получения уведомлений о движении укажите токен бота и ID чата.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div>
            <Label>Токен бота Telegram</Label>
            <Input
              data-testid="telegram-token-input"
              type="password"
              value={settings.telegram_bot_token || ''}
              onChange={(e) => setSettings({ ...settings, telegram_bot_token: e.target.value })}
              className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
              placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            />
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Получите токен у @BotFather в Telegram
            </p>
          </div>

          <div>
            <Label>ID чата Telegram</Label>
            <Input
              data-testid="telegram-chat-id-input"
              value={settings.telegram_chat_id || ''}
              onChange={(e) => setSettings({ ...settings, telegram_chat_id: e.target.value })}
              className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
              placeholder="-1001234567890"
            />
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Используйте @userinfobot для получения ID чата
            </p>
          </div>
        </div>

        <Separator className="bg-[var(--border)]" />

        {/* Storage Settings */}
        <div className="glass p-6 rounded-2xl space-y-4">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Настройки хранения</h2>

          <div>
            <Label>Путь по умолчанию для записей</Label>
            <Input
              data-testid="storage-path-input"
              value={settings.default_storage_path}
              onChange={(e) => setSettings({ ...settings, default_storage_path: e.target.value })}
              className="bg-[var(--bg-tertiary)] border-[var(--border)] text-[var(--text-primary)]"
              placeholder="/app/recordings"
            />
            <p className="text-xs text-[var(--text-secondary)] mt-1">
              Путь, куда будут сохраняться видеозаписи
            </p>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={saving}
            data-testid="save-settings-btn"
            className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white px-8 py-3 rounded-xl"
          >
            {saving ? (
              <div className="flex items-center space-x-2">
                <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                <span>Сохранение...</span>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Save className="w-5 h-5" />
                <span>Сохранить настройки</span>
              </div>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
