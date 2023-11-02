verbs:
OPEN <typeEnum> <size> <gameEnum> <roomname>
JOIN <roomid> <username>
REJOIN <roomid> <clientid>
MARK <clientid> <goalid>
EXIT <clientid>
LIST
GET_GENERATORS <gamename>

server messages:
OPENED <clientid> <boardinfo>
JOINED <clientid> <boardinfo>
REJOINED <boardinfo>
NOAUTH
SHARE 
ERROR <message>
MESSAGE
LISTED