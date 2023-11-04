verbs:
OPEN <typeEnum> <size> <gameEnum> <roomname>
JOIN <roomid> <username>
REJOIN <roomid> <clientid>
MARK <clientid> <goalid>
EXIT <roomid> <clientid>
GENERATE <game> <generator> <boardtype> <seed> 
LIST
GET_GAMES
GET_GENERATORS <game>
MESSAGE <roomid> <clientid> <content>

server messages:
LISTED <rooms>
GAMES <games>
GENERATORS <generators>
OPENED <clientid> <boardinfo>
JOINED <clientid> <boardinfo>
REJOINED <boardinfo>
MEMBERS <members>
SHARE 
NOAUTH
ERROR <message>
MESSAGE <source> <message>
NOTFOUND
BADVERB