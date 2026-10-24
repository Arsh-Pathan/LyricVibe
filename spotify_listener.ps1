Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($asyncOp, $type) {
    $asTask = $asTaskGeneric.MakeGenericMethod($type)
    $netTask = $asTask.Invoke($null, @($asyncOp))
    $netTask.Wait(400) | Out-Null
    if ($netTask.IsCompleted) { return $netTask.Result }
    return $null
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null
$managerOp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
$manager = Await $managerOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$epoch = [DateTimeOffset]::new(1970, 1, 1, 0, 0, 0, [TimeSpan]::Zero)

while ($true) {
    try {
        $sessions = $manager.GetSessions()
        $spotifySession = $null
        foreach ($s in $sessions) {
            if ($s.SourceAppUserModelId -match "Spotify") {
                $spotifySession = $s
                break
            }
        }
        if (-not $spotifySession) {
            $curr = $manager.GetCurrentSession()
            if ($curr -and $curr.SourceAppUserModelId -match "Spotify") {
                $spotifySession = $curr
            }
        }

        if ($spotifySession) {
            $mediaOp = $spotifySession.TryGetMediaPropertiesAsync()
            $media = Await $mediaOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
            $playbackInfo = $spotifySession.GetPlaybackInfo()
            $timeline = $spotifySession.GetTimelineProperties()

            $isPlaying = ($playbackInfo -and $playbackInfo.PlaybackStatus -eq [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionPlaybackStatus]::Playing)
            
            $pos = 0.0
            $updatedEpoch = 0.0
            if ($timeline) {
                $pos = $timeline.Position.TotalSeconds
                if ($timeline.LastUpdatedTime) {
                    $updatedEpoch = ($timeline.LastUpdatedTime - $epoch).TotalSeconds
                }
            }

            $dur = if ($timeline) { $timeline.EndTime.TotalSeconds } else { 0.0 }

            $data = @{
                is_playing = $isPlaying
                track = if ($media) { $media.Title } else { "" }
                artist = if ($media) { $media.Artist } else { "" }
                album = if ($media) { $media.AlbumTitle } else { "" }
                position = [math]::Round($pos, 3)
                updated_at = [math]::Round($updatedEpoch, 3)
                duration = [math]::Round($dur, 3)
            }
            [Console]::WriteLine(($data | ConvertTo-Json -Compress))
        } else {
            [Console]::WriteLine('{"is_playing":false,"track":"","artist":"","album":"","position":0,"updated_at":0,"duration":0}')
        }
    } catch {
        [Console]::WriteLine('{"is_playing":false,"track":"","artist":"","album":"","position":0,"updated_at":0,"duration":0}')
    }
    Start-Sleep -Milliseconds 250
}
