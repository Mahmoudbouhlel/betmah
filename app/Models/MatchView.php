<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class MatchView extends Model
{
     protected $table = 'view_match_details';
    protected $primaryKey = 'match_id';
    public $timestamps = false;
}
