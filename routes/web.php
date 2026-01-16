<?php

use App\Http\Controllers\MatchController;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

 Route::get('/home', function () {
    return Inertia::render('Welcome');
})->name('home');
/*
Route::get('/', function () {
    return Inertia::render('Dashboard');
})->name('dashboard'); */
Route::get('/', [MatchController::class, 'index'])->name('dashboard');
Route::get('/value-bets', [MatchController::class, 'valueBets'])->name('valuebets.index');
Route::get('/top-matches', [MatchController::class, 'topMatches'])->name('top.matches');
Route::get('/over-25', [MatchController::class, 'over25'])->name('over25');
Route::get('/view-matches', [MatchController::class, 'viewMatches'])
    ->name('view.matches');
Route::get('/matches/over25', [MatchController::class, 'viewOver25'])
    ->name('matches.over25');

require __DIR__.'/settings.php';
require __DIR__.'/auth.php';
