# irgateway #

I have a house full of random remotely controllable things that
are controlled by different apps.  WeMo, Hue lights, zwave lights,
etc.

This had a low WAF.

So I hacked together this thing that listens for input events
from cheap remotes similar to this:

http://www.amazon.com/ATian-Remote-Control-Windows-Center/dp/B00ECLVRYQ/

and runs a script on key up/down/hold events and interacts with
openhab (which controls all the different types of items) so
my wife can use an IR remote to control all the different items.

Also, using the windows MCE profile, could be configured on a
harmony remote, I think.

It uses a dumb dsl for the event rules.

This is probably unusable for anyone but me.  Sorry about that.
