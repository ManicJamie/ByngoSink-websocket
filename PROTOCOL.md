verbs:
OPEN <typeEnum> <size> <gameEnum> <roomname>
JOIN <roomid> <username>
REJOIN <roomid> <clientid>
MARK <clientid> <goalid>
EXIT <clientid>
LIST
GET_GAMES
GET_GENERATORS <game>

server messages:
OPENED <clientid> <boardinfo>
JOINED <clientid> <boardinfo>
MEMBERS <members>
REJOINED <boardinfo>
NOAUTH
SHARE 
ERROR <message>
MESSAGE <source> <message>
LISTED
GAMES
GENERATORS
NOTFOUND