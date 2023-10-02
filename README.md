# Spotify Lights Extended
Spotify Lights Extended is an extension of a program written by Yusuf Sezer several years ago. The original program allowed a strip of DotStar LED's to react to whatever track was currently playing on the 
user's Spotify account. This repository is an extension of that code that integrates it to create a broader, general-purpose LED strip decoration controller. It adds the ability to upload, delete, and select
Python scripts to create animations. It also adds a RESTful API via the Flask framework to make controlling the lights as easy as going to a simple website and inputting your choices. 


# How to Install
1. Connect either a DotStar LED strip or NeoPixel LED strip to a Raspberry Pi
2. Create a spotify developers account and create a new application.
4. Get a Spotify Client ID and Secret via the Spotify Developer portal
5. Set up a redirect URI with the spotify portal
   - If these lights will be installed on your home wifi, set the redirect URI to `http://<IP_ADDRESS_OF_PI>/spotifyredirect`
   - If these lights will be set up in a location where devices cannot directly communicate (such as eduroam) then you have to set up a [cloudflare tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/) and set the spotify redirect URI to `http://<HOST_NAME>/spotifyredirect`
7. Clone this repository onto the Raspberry Pi
8. Run `pip install -r requirements.txt`
9. Enter the Spotify Client ID, Secret, and redirect URI into [credentials.py](src/Files/credentials.py)
10. Copy the [SpotifyLights.service](./SpotifyLights.service) file into `/etc/systemd/system/` folder
11. Run command `sudo systemctl enable SpotifyLights.service` and then `sudo systemtctl start SpotifyLights.service`

And then the lights should work.
