;SDL
;// ============================================================================
;// empty_vehicle_highlight
;// Marks every entity built on /properties/vehicle.ext (no type filter)
;// that currently has no crew and is shown on the minimap:
;//   a proxy entity "evh_<vehicle name>" with the vehicle's own model,
;//      spawned at the vehicle's "basis" bone. It is a stuff item, so the
;//      vanilla "highlight items" key (C) outlines it, and hovering shows the
;//      vehicle name. Proxies are generated per vehicle by tools/gen_proxies.py
;//      into empty_vehicle_highlight_proxies.inc
;//      ({"<name> obstacle_ignore_height" {on "evh_proxy"}}); proxy entities live
;//      in /entity/evh/, items in /set/stuff/evh/ (outside the library's scan).
;//      A proxy lives 3.3 s and is re-spawned every 3 s while the vehicle
;//      stays empty, so it disappears by itself once the vehicle is crewed.
;//
;// Block key "vehicle obstacle_ignore_height": both props come from
;// /properties/vehicle.ext, so the block applies to everything built on it,
;// without re-using the vanilla "vehicle" key.
;//
;// Tunables:
;//   refresh period      : "delay 3" below / proxy lifetime in the proxies file
;// ============================================================================

{"vehicle obstacle_ignore_height"
	{on spawn
		;// crew of pre-placed vehicles may be seated after spawn
		{delay 2 {call "evh_tick"}}
	}

	{on operatable off
		{delay 1 {call "evh_tick"}}
	}
	{on operatable on
		{call "evh_tick"}
	}

	;// default (no-op) so vehicles without a generated proxy block are safe
	{on "evh_proxy"}

	{on "evh_tick"
		{kill_delay "evh_loop"}
		{if not operatable
			;// same exclusions as the minimap entity filter
			{if able "minimap"
				{if not tagged "destroyed"
					{if not prop "no_minimap_view"
						{call "evh_proxy"}
						{delay 3 "evh_loop" {call "evh_tick"}}
					}
				}
			}
		}
	}
}
