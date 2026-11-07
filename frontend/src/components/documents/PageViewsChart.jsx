import { useTranslation } from 'react-i18next';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/Tooltip';
import { formatDate } from '../../utils/formatters';

function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function PageViewsChart({ pageViews, documentType }) {
  const { t } = useTranslation();

  if (!pageViews || pageViews.length === 0) {
    return <p className="text-sm text-muted-foreground">{t('viewSessions.noPageViewData')}</p>;
  }

  const isVideo = documentType === 'video' || pageViews[0]?.media_type === 'video';

  if (isVideo) {
    const formatTime = (timeInSecs) => {
      if (timeInSecs == null) return "00:00";
      const m = Math.floor(timeInSecs / 60);
      const s = Math.floor(timeInSecs % 60);
      return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    };

    const totalVideoDuration = pageViews.reduce((sum, v) => sum + v.duration_seconds, 0);

    return (
      <div className="space-y-3">
        <p className="text-sm font-medium text-foreground">
          {t('viewSessions.totalTimeWatched', { duration: formatDuration(totalVideoDuration) })}
        </p>
        <div className="overflow-x-auto rounded border">
          <table className="min-w-full divide-y divide-border text-xs text-foreground">
            <thead>
              <tr className="bg-muted text-muted-foreground uppercase font-semibold text-[10px] tracking-wider">
                <th className="px-3 py-2 text-left">{t('viewSessions.eventTime')}</th>
                <th className="px-3 py-2 text-left">{t('viewSessions.playbackTimespan')}</th>
                <th className="px-3 py-2 text-right">{t('viewSessions.duration')}</th>
                <th className="px-3 py-2 text-center">{t('viewSessions.audio')}</th>
                <th className="px-3 py-2 text-center">{t('viewSessions.screen')}</th>
                <th className="px-3 py-2 text-center">{t('viewSessions.speed')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-card">
              {pageViews.map((view, idx) => (
                <tr key={view.id || idx} className="hover:bg-muted">
                  <td className="px-3 py-2 whitespace-nowrap">{formatDate(view.created_at, 'PP p')}</td>
                  <td className="px-3 py-2 whitespace-nowrap font-mono">
                    {formatTime(view.video_start_time)} - {formatTime(view.video_end_time)}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-right font-medium">
                    {view.duration_seconds}s
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-center">
                    {view.video_volume === 0 ? (
                      <span className="inline-flex items-center rounded-full bg-danger-subtle px-2 py-0.5 text-danger font-medium">{t('viewSessions.muted')}</span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-success-subtle px-2 py-0.5 text-success font-medium">
                        {view.video_volume != null ? `${view.video_volume}%` : t('viewSessions.soundOn')}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-center">
                    {view.is_fullscreen ? (
                      <span className="inline-flex items-center rounded-full bg-info-subtle px-2 py-0.5 text-info font-medium">{t('viewSessions.fullscreen')}</span>
                    ) : (
                      <span className="text-muted-foreground">{t('viewSessions.standard')}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-center font-mono">
                    {view.playback_speed ? `${view.playback_speed}x` : '1.0x'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const isMarkdown = documentType === 'markdown' || pageViews[0]?.media_type === 'markdown';

  // Aggregate views by page_number to prevent duplicate key warnings
  const uniquePageViews = Object.values(
    pageViews.reduce((acc, { page_number, duration_seconds, url, scroll_percentage }) => {
      if (acc[page_number]) {
        acc[page_number].duration_seconds += duration_seconds;
        if (scroll_percentage != null) {
          acc[page_number].scroll_percentage = Math.max(
            acc[page_number].scroll_percentage ?? 0,
            scroll_percentage
          );
        }
        // Prefer a valid URL if the existing one is missing.
        if (!acc[page_number].url && url) {
          acc[page_number].url = url;
        }
      } else {
        acc[page_number] = { page_number, url, duration_seconds, scroll_percentage };
      }
      return acc;
    }, {})    
  );

  const maxDuration = Math.max(...uniquePageViews.map((v) => v.duration_seconds), 0);
  const totalDuration = uniquePageViews.reduce((sum, v) => sum + v.duration_seconds, 0);

  return (
    <TooltipProvider>
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">
          {t('viewSessions.totalTimeSpent', { duration: formatDuration(totalDuration) })}
        </p>
        <div className="space-y-1">
          {uniquePageViews
            .sort((a, b) => a.page_number - b.page_number)
            .map((view) => (
              <div key={view.page_number} className="flex items-center gap-4 text-sm">
                <span className="w-20 flex-shrink-0 text-right text-muted-foreground truncate" title={isMarkdown ? (view.scroll_percentage != null ? `${t('viewSessions.readingDepth', { defaultValue: 'Read depth' })} ${view.scroll_percentage}%` : t('viewSessions.document', { defaultValue: 'Document' })) : t('viewSessions.pageNumber', { number: view.page_number })}>
                  {isMarkdown ? (
                    view.scroll_percentage != null ? `${view.scroll_percentage}%` : t('viewSessions.document', { defaultValue: 'Document' })
                  ) : (
                    t('viewSessions.pageNumber', { number: view.page_number })
                  )}
                </span>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="h-4 flex-grow cursor-pointer rounded bg-border">
                      <div
                        className="h-4 rounded bg-info"
                        style={{
                          width: maxDuration > 0 ? `${(view.duration_seconds / maxDuration) * 100}%` : '0%',
                        }}
                      />
                    </div>
                  </TooltipTrigger>
                  {(view.url || (isMarkdown && view.scroll_percentage != null)) && (
                    <TooltipContent>
                      {view.url ? (
                        <img
                          src={view.url}
                          alt={`Page ${view.page_number} preview`}
                          className="h-48 w-auto rounded"
                        />
                      ) : (
                        <p className="text-xs">{t('viewSessions.readingDepth', { defaultValue: 'Read depth' })}: {view.scroll_percentage}%</p>
                      )}
                    </TooltipContent>
                  )}
                </Tooltip>
                <span className="w-16 flex-shrink-0 text-left font-medium text-foreground">
                  {formatDuration(view.duration_seconds)}
                </span>
              </div>
            ))}
        </div>
      </div>
    </TooltipProvider>
  );
}
