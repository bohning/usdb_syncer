# Meta Tags

The goal of this project is to make adding new songs to your UltraStar collection as
convenient as possible. To this purpose it introduces the concept of meta tags. Txt files
on [USDB](http://usdb.animux.de) can include these tags to specify which online
resources, like sound and image files, are needed and how they should be processed to
make a complete song folder.

## Format

Meta tags are stored inside the `#VIDEO` tag of a txt file and are a comma-separated
list of `key=value` pairs. If the `value` part has multiple components, they are separated
by `-`. The table below contains the currently recognized tags and
their allowed values.

| Tag                        | Key         | Allowed Values                                              |
| -------------------------- | ----------- | ----------------------------------------------------------- |
| Audio resource             | a           | URL or YouTube id                                           |
| Video resource             | v           | URL or YouTube id                                           |
| Video trimming             | v-trim      | Decimal numbers (seconds): `start-end`                      |
| Video trimming             | v-crop      | Integers: `left-right-top-bottom`                           |
| Cover resource             | co          | URL or FanArt id                                            |
| Protocol of cover URL      | co-protocol | `http`                                                      |
| Cover rotation             | co-rotate   | Decimal number (angle)                                      |
| Cover cropping             | co-crop     | Integers: `left-upper-wide-height` ([see below](#cropping)) |
| Cover resizing             | co-resize   | Integers: `wide-height`                                     |
| Cover contrast             | co-contrast | `auto` or a decimal number                                  |
| Background resource        | bg          | URL or FanArt id                                            |
| Protocol of background URL | bg-protocol | `http`                                                      |
| Background cropping        | bg-crop     | Integers: `left-upper-wide-height` ([see below](#cropping)) |
| Background resizing        | bg-resize   | Integers: `wide-height`                                     |
| Name of first player       | p1          | Name or nothing                                             |
| Name of second player      | p2          | Name or nothing                                             |

Since USDB enforces a certain line length, there are some conventions to reduce redundant
text in meta tags:

1. URLs must not contain the protocol name. E.g. if the URL is `https://www.wikipedia.org`,
   the tag value should be `www.wikipedia.org`. The assumed protocol is `https`. If the
   URL should require a different one, the `-protocol` tags can be used, e.g.
   `co-protocol=http`.
2. Links to videos from YouTube and images from <https://fanart.tv> only require an id.
   E.g. if the video URL is `https://www.youtube.com/watch?v=dQw4w9WgXcQ`,
   `v=dQw4w9WgXcQ` would be sufficient as a tag.

## Examples

Lots of songs on USDB already have meta tags. You can look at
[these](http://usdb.animux.de/index.php?link=list&user=334) for example, to see how they
work in practice (requires login).

### Cropping

Let's say you have an image 1000 px wide and 2000 px heigh. As covers should be quadratic,
you want to remove 200 px at the top and 800 px at the bottom. To achieve that, we have
to start at the pixel that is 0 px removed from the left border and 200 px removed from
the top border. Then we take 1000 px both in width and height.

The resulting tag would be `co-crop=0-200-1000-1000`.
