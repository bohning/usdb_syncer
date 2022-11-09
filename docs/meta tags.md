# Meta Tags

The goal of this project is to make adding new songs to your UltraStar collection as
convenient as possible. To this purpose it introduces the concept of meta tags. Txt files
on [USDB](http://usdb.animux.de) can include these tags to specify which online
resources, like sound and image files, are needed and how they should be processed to
make a complete song folder. It further correctly handles duets by adding `P1` and `P2` in the appropriate places when the song is a duet.

## Format

Meta tags are stored inside the `#VIDEO` tag of a txt file and are a comma-separated
list of `key=value` pairs. If the `value` part has multiple components, they are separated
by `-`. The table below contains the currently recognized tags and
their allowed values.

| Tag                        | Key           | Allowed Values                                               | Examples                       |
| -------------------------- | ------------- | -------------------------------------------------------------------- | ------------------------------ |
| Audio resource             | `a`           | YouTube id (preferred) or URL (use audio from this source)           | `a=1k8craCGpgs`                |
| Video resource             | `v`           | YouTube id (preferred) or URL (if `a` is not present, use audio+video from this source, otherwise use video from this source)                                           | `v=yCC_b5WHLX0`,<br />`v=vimeo.com/163118371` |
| Video trimming             | `v-trim`      | Integers (frames), seconds.milliseconds or minutes:seconds.milliseconds: `start-end` | `trim=10-5768`,<br />`trim=10-`,<br />`trim=-5768`,<br />`trim=00:04.120-`,<br />`trim=-05:02.960` |
| Video cropping             | `v-crop`      | Integers: `left-right-top-bottom`                                     | `v-crop=0-0-120-120` (e.g. remove top and bottom black bars),<br />`v-crop=50-50-0-0` (e.g. remove left and right black bars) |
| Cover resource             | `co`          | fanart.tv id (preferred) or URL                                       | `co=dont-stop-believin-60c8e39272ab9.jpg` |
| Protocol of cover URL      | `co-protocol` | `http`                                                                | `co-protocol=http`             |
| Cover rotation             | `co-rotate`   | Decimal number (angle in degrees, counterclockwise)                   | `co-rotate=-0.3`               |
| Cover cropping             | `co-crop`     | Integers (Pixels): `left-top-width-height` ([see below](#cropping))   | `co-crop=10-10-1000-1000`      |
| Cover resizing             | `co-resize`   | Integers (Pixels): `width-height`                                     | `co-resize=1920-1920`          |
| Cover contrast             | `co-contrast` | `auto` or a decimal number                                            | `co-contrast=1.2`              |
| Background resource        | `bg`          | fanart.tv id (preferred) or URL                                       | `bg=journey-510f62efe4879.jpg` |
| Protocol of background URL | `bg-protocol` | `http`                                                                | `bg-protocol=http`             |
| Background cropping        | `bg-crop`     | Integers (Pixels): `left-upper-width-height` ([see below](#cropping)) | `bg-crop=10-10-1920-1080`      |
| Background resizing        | `bg-resize`   | Integers (Pixels): `width-height`                                     | `bg-resize=1920-1080`          |
| Name of 1. singer (duets)  | `p1`          | Name or e.g. P1                                                       | `p1=Elton John`                |
| Name of 2. singer (duets)  | `p2`          | Name or e.g. P2                                                       | `p2=Kiki Dee`                  |

Since some characters have a special meaning (`#`, `:`, `,`) or are forbidden (`/`) and since there is a certain maximum line length (~170 characters), there are certain conventions:

1. URLs must not contain the protocol name. E.g. if the URL is `https://www.wikipedia.org`,
   the tag value should be `www.wikipedia.org`. The assumed protocol is `https`. If the
   URL should require a different one, the `-protocol` tags can be used, e.g.
   `co-protocol=http`.
2. URLs may not contain commas (`,`) or colons (`:`)
2. Links to videos from YouTube and images from <https://fanart.tv> only require an id.
   E.g. if the video URL is `https://www.youtube.com/watch?v=dQw4w9WgXcQ`,
   `v=dQw4w9WgXcQ` would be sufficient as a tag.

## Examples

Lots of songs on USDB already have meta tags. You can look at
[these](http://usdb.animux.de/index.php?link=list&user=334) for example, to see how they
work in practice (requires login).

### Cropping

Let’s say you have an image 1000 px wide and 2000 px height. As covers should be quadratic,
you want to remove 200 px at the top and 800 px at the bottom. To achieve that, we have
to start at the pixel that is 0 px removed from the left border and 200 px removed from
the top border. Then we take 1000 px both in width and height.

The resulting tag would be `co-crop=0-200-1000-1000`.
