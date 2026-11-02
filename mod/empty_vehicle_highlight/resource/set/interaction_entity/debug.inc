;/*=========== Generic Debug Defines ===========*/

(define "+tag-"
	{tags add "%0"}
	{delay %1
		{tags remove "%0"}
	}
)

;// mod empty_vehicle_highlight: hooked here instead of entity.set for compatibility
(include "empty_vehicle_highlight.inc")
(include "empty_vehicle_highlight_proxies.inc")
