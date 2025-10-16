import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import axios from 'axios';
import { Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CameraSettingsDialog = ({ camera, open, onClose, onSave }) => {
  const [settings, setSettings] = useState({
    name: camera.name,
    url: camera.url,
    username: camera.username || '',
    password: camera.password || '',
    motion: camera.motion || {
      enabled: false,
      mog2: {
        history: 500,
        var_threshold: 16,
        detect_shadows: true,
        learning_rate: -1,
        n_mixtures: 5,
      },
      min_area: 500,
      min_duration_seconds: 1,
      exclusion_zones: [],
    },
    recording: camera.recording || {
      continuous: false,
      on_motion: true,
      storage_path: '/app/recordings',
      max_file_duration_minutes: 60,
    },
    telegram: camera.telegram || {
      send_alerts: false,
      send_video_clips: false,
    },
  });

  const handleSave = async () => {
    try {
      await axios.put(`${API}/cameras/${camera.id}`, settings);
      toast.success('Настройки сохранены');
      onSave();
    } catch (error) {
      toast.error('Ошибка сохранения настроек');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-[var(--bg-secondary)] border-[var(--border)] text-[var(--text-primary)]">
        <DialogHeader>
          <DialogTitle>Настройки камеры - {camera.name}</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="basic" className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-[var(--bg-tertiary)]">
            <TabsTrigger value="basic">Основные</TabsTrigger>
            <TabsTrigger value="motion">Движение</TabsTrigger>
            <TabsTrigger value="recording">Запись</TabsTrigger>
            <TabsTrigger value="telegram">Telegram</TabsTrigger>
          </TabsList>

          {/* Basic Settings */}
          <TabsContent value="basic" className="space-y-4">
            <div>
              <Label>Название</Label>
              <Input
                data-testid="edit-camera-name"
                value={settings.name}
                onChange={(e) => setSettings({ ...settings, name: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)]"
              />
            </div>
            <div>
              <Label>URL</Label>
              <Input
                data-testid="edit-camera-url"
                value={settings.url}
                onChange={(e) => setSettings({ ...settings, url: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)]"
              />
            </div>
            <div>
              <Label>Имя пользователя</Label>
              <Input
                value={settings.username}
                onChange={(e) => setSettings({ ...settings, username: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)]"
              />
            </div>
            <div>
              <Label>Пароль</Label>
              <Input
                type="password"
                value={settings.password}
                onChange={(e) => setSettings({ ...settings, password: e.target.value })}
                className="bg-[var(--bg-tertiary)] border-[var(--border)]"
              />
            </div>
          </TabsContent>

          {/* Motion Detection Settings */}
          <TabsContent value="motion" className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Включить детекцию движения</Label>
              <Switch
                data-testid="motion-enabled-switch"
                checked={settings.motion.enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, motion: { ...settings.motion, enabled: checked } })
                }
              />
            </div>

            {settings.motion.enabled && (
              <>
                <div className="space-y-4 p-4 bg-[var(--bg-tertiary)] rounded-lg">
                  <h3 className="font-semibold">Параметры MOG2</h3>

                  <TooltipProvider>
                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <Label>История кадров: {settings.motion.mog2.history}</Label>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="w-4 h-4 text-[var(--text-secondary)]" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Количество последних кадров, используемых для моделирования фона.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Slider
                        value={[settings.motion.mog2.history]}
                        onValueChange={([value]) =>
                          setSettings({
                            ...settings,
                            motion: {
                              ...settings.motion,
                              mog2: { ...settings.motion.mog2, history: value },
                            },
                          })
                        }
                        min={100}
                        max={1000}
                        step={50}
                      />
                    </div>

                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <Label>Порог дисперсии: {settings.motion.mog2.var_threshold}</Label>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="w-4 h-4 text-[var(--text-secondary)]" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Порог для определения, насколько пиксель отличается от фона.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Slider
                        value={[settings.motion.mog2.var_threshold]}
                        onValueChange={([value]) =>
                          setSettings({
                            ...settings,
                            motion: {
                              ...settings.motion,
                              mog2: { ...settings.motion.mog2, var_threshold: value },
                            },
                          })
                        }
                        min={1}
                        max={50}
                        step={1}
                      />
                    </div>

                    <div>
                      <div className="flex items-center space-x-2 mb-2">
                        <Label>Количество гауссовых компонент: {settings.motion.mog2.n_mixtures}</Label>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="w-4 h-4 text-[var(--text-secondary)]" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Количество гауссовых распределений для моделирования каждого пикселя.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Slider
                        value={[settings.motion.mog2.n_mixtures]}
                        onValueChange={([value]) =>
                          setSettings({
                            ...settings,
                            motion: {
                              ...settings.motion,
                              mog2: { ...settings.motion.mog2, n_mixtures: value },
                            },
                          })
                        }
                        min={1}
                        max={10}
                        step={1}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Label>Детектировать тени</Label>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="w-4 h-4 text-[var(--text-secondary)]" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Включить детекцию теней для уменьшения ложных срабатываний.</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Switch
                        checked={settings.motion.mog2.detect_shadows}
                        onCheckedChange={(checked) =>
                          setSettings({
                            ...settings,
                            motion: {
                              ...settings.motion,
                              mog2: { ...settings.motion.mog2, detect_shadows: checked },
                            },
                          })
                        }
                      />
                    </div>
                  </TooltipProvider>
                </div>

                <div>
                  <Label>Минимальная площадь объекта (px): {settings.motion.min_area}</Label>
                  <Slider
                    value={[settings.motion.min_area]}
                    onValueChange={([value]) =>
                      setSettings({ ...settings, motion: { ...settings.motion, min_area: value } })
                    }
                    min={100}
                    max={5000}
                    step={100}
                  />
                </div>

                <div>
                  <Label>Игнорировать движения короче (sec): {settings.motion.min_duration_seconds}</Label>
                  <Slider
                    value={[settings.motion.min_duration_seconds]}
                    onValueChange={([value]) =>
                      setSettings({
                        ...settings,
                        motion: { ...settings.motion, min_duration_seconds: value },
                      })
                    }
                    min={0}
                    max={10}
                    step={1}
                  />
                </div>

                <div>
                  <Label>Предзапись (сек): {settings.motion.pre_record_seconds}</Label>
                  <p className="text-xs text-[var(--text-secondary)] mb-2">
                    Запись начнется за N секунд до обнаружения движения
                  </p>
                  <Slider
                    value={[settings.motion.pre_record_seconds || 5]}
                    onValueChange={([value]) =>
                      setSettings({
                        ...settings,
                        motion: { ...settings.motion, pre_record_seconds: value },
                      })
                    }
                    min={0}
                    max={30}
                    step={1}
                  />
                </div>

                <div>
                  <Label>Постзапись (сек): {settings.motion.post_record_seconds}</Label>
                  <p className="text-xs text-[var(--text-secondary)] mb-2">
                    Запись продолжится N секунд после окончания движения
                  </p>
                  <Slider
                    value={[settings.motion.post_record_seconds || 10]}
                    onValueChange={([value]) =>
                      setSettings({
                        ...settings,
                        motion: { ...settings.motion, post_record_seconds: value },
                      })
                    }
                    min={0}
                    max={60}
                    step={5}
                  />
                </div>
              </>
            )}
          </TabsContent>

          {/* Recording Settings */}
          <TabsContent value="recording" className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Непрерывная запись</Label>
              <Switch
                data-testid="continuous-recording-switch"
                checked={settings.recording.continuous}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, recording: { ...settings.recording, continuous: checked } })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <Label>Запись по движению</Label>
              <Switch
                data-testid="motion-recording-switch"
                checked={settings.recording.on_motion}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, recording: { ...settings.recording, on_motion: checked } })
                }
              />
            </div>

            <div>
              <Label>Путь для сохранения</Label>
              <Input
                value={settings.recording.storage_path}
                onChange={(e) =>
                  setSettings({ ...settings, recording: { ...settings.recording, storage_path: e.target.value } })
                }
                className="bg-[var(--bg-tertiary)] border-[var(--border)]"
              />
            </div>

            <div>
              <Label>Макс. длительность файла (min): {settings.recording.max_file_duration_minutes}</Label>
              <Slider
                value={[settings.recording.max_file_duration_minutes]}
                onValueChange={([value]) =>
                  setSettings({
                    ...settings,
                    recording: { ...settings.recording, max_file_duration_minutes: value },
                  })
                }
                min={5}
                max={180}
                step={5}
              />
            </div>
          </TabsContent>

          {/* Telegram Settings */}
          <TabsContent value="telegram" className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Отправлять уведомления о движении</Label>
              <Switch
                data-testid="telegram-alerts-switch"
                checked={settings.telegram.send_alerts}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, telegram: { ...settings.telegram, send_alerts: checked } })
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <Label>Отправлять видео клипы</Label>
              <Switch
                data-testid="telegram-video-switch"
                checked={settings.telegram.send_video_clips}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, telegram: { ...settings.telegram, send_video_clips: checked } })
                }
              />
            </div>

            <div className="p-4 bg-[var(--bg-tertiary)] rounded-lg">
              <p className="text-sm text-[var(--text-secondary)]">
                Настройки Telegram (токен бота и ID чата) настраиваются в глобальных настройках системы.
              </p>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end space-x-2 mt-6">
          <Button onClick={onClose} variant="outline" className="border-[var(--border)]">
            Отмена
          </Button>
          <Button onClick={handleSave} data-testid="save-camera-settings" className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white">
            Сохранить
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CameraSettingsDialog;
