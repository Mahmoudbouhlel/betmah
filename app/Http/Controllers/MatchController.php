<?php

namespace App\Http\Controllers;

use App\Models\FootballMatch;
use Illuminate\Http\Request;
use App\Models\H2hMatch;
use App\Models\Standing;
use Carbon\Carbon;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;

class MatchController extends Controller
{
public function index()
{
    $allMatches = collect();
    $allH2H = collect();
    $allStandings = collect();

    // ✅ backend count (no frontend change required)
    $matchesCount = 0;

    DB::table('matches as m')
        ->leftJoin('leagues as l', 'l.id', '=', 'm.league_id')
        ->select(
            'm.id',
            'm.match_key',
            'm.home_team',
            'm.away_team',
            'm.match_date',
            'm.match_time',
            'm.home_odds',
            'm.draw_odds',
            'm.away_odds',
            'm.match_url',
            'm.scraped_at',
            DB::raw("COALESCE(l.full_name,'Unknown') as league")
        )
        ->orderBy('m.match_date', 'asc')
        ->orderBy('m.match_time', 'asc')
        ->chunk(100, function ($matches) use (&$allMatches, &$allH2H, &$allStandings, &$matchesCount) {

            $matchesCount += $matches->count(); // ✅ count per chunk

            $allMatches = $allMatches->merge($matches);

            $matchIds = collect($matches)->pluck('id')->toArray();

            $allH2H = $allH2H->merge(
                H2hMatch::whereIn('match_id', $matchIds)->get()
            );

            $allStandings = $allStandings->merge(
                Standing::whereIn('match_id', $matchIds)->get()
            );
        });

    $leagues = DB::table('leagues')
        ->select('id', 'full_name')
        ->orderBy('full_name', 'asc')
        ->get();

    return Inertia::render('Dashboard', [
        'matches'      => $allMatches,
        'h2hMatches'   => $allH2H,
        'standings'    => $allStandings,
        'leagues'      => $leagues,

        // ✅ backend value available to Vue if you want it
        'matchesCount' => $matchesCount,
    ]);
}


}
