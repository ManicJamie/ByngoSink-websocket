verbs:
OPEN <typeEnum> <size> <gameEnum> <roomname>
JOIN <roomid> <username>
REJOIN <roomid> <clientid>
EXIT <roomid> <clientid>
GENERATE <game> <generator> <boardtype> <seed> 
LIST
GET_GAMES
GET_GENERATORS <game>
MESSAGE <roomid> <clientid> <content>
CREATE_TEAM <roomid> <clientid> <color> 
JOIN_TEAM <roomid> <teamid>
LEAVE_TEAM <roomid>
SPECTATE <roomid>
MARK <roomid> <goalid>

server messages:
LISTED <rooms>
GAMES <games>
GENERATORS <generators>
OPENED <clientid> <boardinfo>
JOINED <clientid> <boardinfo>
REJOINED <boardinfo>
MEMBERS <members> <teams>
UPDATE <boardinfo>
NOAUTH
ERROR <message>
MESSAGE <source> <message>
NOTFOUND
BADVERB
TEAM_CREATED
TEAM_JOINED
TEAM_LEFT
NOTEAM