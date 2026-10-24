Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($asyncOp, $type) {
    $asTask = $asTaskGeneric.MakeGenericMethod($type)
    $netTask = $asTask.Invoke($null, @($asyncOp))
    $netTask.Wait(1200) | Out-Null
    if ($netTask.IsCompleted) { return $netTask.Result }
    return $null
}

[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType = WindowsRuntime] | Out-Null
$managerOp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
$manager = Await $managerOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$epoch = [DateTimeOffset]::new(1970, 1, 1, 0, 0, 0, [TimeSpan]::Zero)

$lastTitle = ""
$lastArtist = ""
$lastAlbum = ""

while ($true) {
    try {
        if (-not $manager) {
            $managerOp = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
            $manager = Await $managerOp ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
        }

        $sessions = if ($manager) { $manager.GetSessions() } else { @() }
        $spotifySession = $null
        foreach ($s in $sessions) {
            if ($s.SourceAppUserModelId -match "Spotify") {
                $spotifySession = $s
                break
            }
        }
        if (-not $spotifySession -and $manager) {
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
            
            if ($media -and $media.Title) {
                $lastTitle = $media.Title
                $lastArtist = $media.Artist
                $lastAlbum = $media.AlbumTitle
            }

            $currentTrack = if ($media -and $media.Title) { $media.Title } elseif ($isPlaying -and $lastTitle) { $lastTitle } else { "" }
            $currentArtist = if ($media -and $media.Artist) { $media.Artist } elseif ($isPlaying -and $lastArtist) { $lastArtist } else { "" }
            $currentAlbum = if ($media -and $media.AlbumTitle) { $media.AlbumTitle } elseif ($isPlaying -and $lastAlbum) { $lastAlbum } else { "" }

            $pos = 0.0
            $updatedEpoch = 0.0
            if ($timeline) {
                $pos = $timeline.Position.TotalSeconds
                if ($timeline.LastUpdatedTime) {
                    $updatedEpoch = ($timeline.LastUpdatedTime - $epoch).TotalSeconds
                }
                # SMTC Position is FROZEN at last state-change (play/pause/seek).
                # Compute TRUE real-time position by adding elapsed since LastUpdatedTime.
                if ($isPlaying -and $timeline.LastUpdatedTime) {
                    $nowOffset = [DateTimeOffset]::UtcNow
                    $elapsed = ($nowOffset - $timeline.LastUpdatedTime).TotalSeconds
                    if ($elapsed -gt 0 -and $elapsed -lt 600) {
                        $pos = $pos + $elapsed
                    }
                }
            }

            $dur = if ($timeline) { $timeline.EndTime.TotalSeconds } else { 0.0 }
            # Clamp position to duration
            if ($dur -gt 0 -and $pos -gt $dur) { $pos = $dur }

            $data = @{
                is_playing = $isPlaying
                track = $currentTrack
                artist = $currentArtist
                album = $currentAlbum
                position = [math]::Round($pos, 3)
                updated_at = [math]::Round($updatedEpoch, 3)
                duration = [math]::Round($dur, 3)
            }
            [Console]::WriteLine(($data | ConvertTo-Json -Compress))
        } else {
            $lastTitle = ""
            $lastArtist = ""
            $lastAlbum = ""
            [Console]::WriteLine('{"is_playing":false,"track":"","artist":"","album":"","position":0,"updated_at":0,"duration":0}')
        }
    } catch {
        $manager = $null
        [Console]::WriteLine('{"is_playing":false,"track":"","artist":"","album":"","position":0,"updated_at":0,"duration":0}')
    }
    Start-Sleep -Milliseconds 250
}
