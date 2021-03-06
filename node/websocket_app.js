var WebSocketServer = require('ws').Server;
var net = require('net');
var url = require('url');
var util = require('util'); // util.inspect
var Kegerator = require('./models/kegerator');

var kegConnections = {};

module.exports = function(server) {
  var wss = new WebSocketServer({
    server: server,
    path: '/sockets'
  });

  var activeKegerator = null;

  wss.on('connection', connectionListener);
};

// error factory for initial connection errors
var initErrorFactory = function(reject_func) {
  return function(err) {
    reject_func(err);
  };
};

var SocketConnection = function(id, client) {
  console.log("new socket connection created");
  this.id = id;
  this.client = client;

  client.on('data', function(_this) {
    return function(data) {
      console.log('data');
      console.log(data);
    };
  }(this));
  client.on('close', function(_this) {
    return function() {
      console.log('socket closed');
      delete SocketConnection.connections[_this.id];
      console.log('close');
    };
  }(this));
  client.on('error', function(_this) {
    return function(error) {
      console.log('error');
      console.log(error);
    };
  }(this));

  SocketConnection.connections[id] = this;
};

SocketConnection.connections = {};

SocketConnection.createNew = function(id, port, host) {
  console.log("attempting to create new");
  if(id in SocketConnection.connections) {
    throw new Error('duplicate id in connections');
  }
  var defaultTimeout = 15000; // 15 seconds
  var timeoutPromise = new Promise(function(resolve, reject) {
    return setTimeout(function() {
      var err = new Error('creation timed out after ' + defaultTimeout / 1000 + ' seconds');
      err.code = 'TIMEOUT';
      reject(err);
    }, defaultTimeout);
  });

  var creationPromise = new Promise(function(resolve, reject) {
    var initError = initErrorFactory(reject);
    var client = net.createConnection({
      port: port,
      host: host
    }, function(resolve_func) {
      return function() {
        client.removeListener('error', initError);
        return resolve_func(new SocketConnection(id, client));
      };
    }(resolve));

    client.on('error', initError);
  });

  return Promise.race([timeoutPromise, creationPromise]);
};

var probeKegerator = function(id, address, port, timeout) {
  if(id in SocketConnection.connections) {
    return Promise.resolve(SocketConnection.connections[id].client);
  } else {
    return SocketConnection.createNew(id, port, address).then(function(newSocketConnection) {
      console.log("client returned");
      return newSocketConnection.client;
    });
  }
};

var activateKeg = function(obj) {
  return Kegerator.findById(obj.id).then(function(kegerator) {
    var response = {kegerator: kegerator, action: 'activate_keg'};
    if(kegerator) {
      // probe with default timeout of one minute
      return probeKegerator(kegerator._id, kegerator.address, kegerator.port).then(function(client_result) {
        // probe succeeded
        response.message = 'probe succeeded';
        response.status = 'ok';

        kegConnections[kegerator._id] = {
          client: client_result,
          lastProbed: Date.now()
        };

        return response;
      }).catch(function(err) {
        // probe failed
        response.message = 'probe failed with code: "' + err.code + '"';
        response.status = 'fail';
        return response;
      });
    } else {
      // not found
      response.message = 'keg with id "' + obj.id + '"not found';
      response.status = 'fail';
      return Promise.resolve(response);
    }
  }).catch(function(mongo_err) {
    console.log('mongo error');
  });
};

var determineAction = function(actionName, data) {
  switch (actionName) {
    case "activate_keg":
      return activateKeg(data);
    default: 
      return Promise.resolve({
        message: "unknown action"
      });
  }
};

var parseMessage = function(message, jsonOnly) {
  var parsedMessage;
  try {
    parsedMessage = JSON.parse(message);
  } catch (e) {
    parsedMessage = jsonOnly ? null : message;
  }
  if(parsedMessage === null) {
    return Promise.reject({
      message: "invalid json"
    });
  } else {
    return Promise.resolve(parsedMessage);
  }
};

var messageListenerFactory = function(ws) {
  return function(message) {
    return parseMessage(message, true).then(function(result) {
      console.log(result);
      if('action' in result) {
        return determineAction(result.action, result.data).then(function(action_result) {
          console.log('action result');
          console.log(action_result);
          ws.send(JSON.stringify(action_result));
        });
      } else {
        console.log('unknown');
        console.log(result);
      }
    });
  };
};

var connectionListener = function(ws) {
  ws.on('message', messageListenerFactory(ws));
};

var connectionListener1 = function(ws) {
  var loc = url.parse(ws.upgradeReq.url, true);

  ws.on('message', function(message) {
    var parsed;
    ws.send(JSON.stringify({
      type: 'message',
      message: 'received: ' + message
    }));

    try {
      parsed = JSON.parse(message);
    } catch (e) {
      return;
    }

    if(!parsed) {
      return;
    }

    if(parsed.currentHash && parsed.currentHash === "pouring") {
      if(activeKegerator !== null) {
        ws.send(JSON.stringify({
          type: "message",
          message: "begin pouring..."
        }));
      } else {
        ws.send(JSON.stringify({
          type: "message",
          message: "you must first set up kegerator"
        }));
      }
    } else if (parsed.activeKeg) {
      Kegerator.findById(parsed.activeKeg).then(function(result) {
        if(result) {
          activeKegerator = new net.Socket();
          activeKegerator.connect(result.port, result.address, function(err) {
            if(err) {
              return console.log(err);
            }
            ws.send(JSON.stringify({
              activeKeg: result.toJSON()
            }));
          });
          activeKegerator.on('error', function(err) {
            ws.send(JSON.stringify({
              type: 'message',
              message: 'failed to connect to "' + result.name + '"'
            }));
            activeKegerator = null;
          });
        } else {
          ws.send(JSON.stringify({
            type: "message",
            message: "kegerator not found"
          }));
        }

      }).catch(function(error) {
        ws.send(JSON.stringify({
          type: 'message',
          message: 'failed: ' + util.inspect(error)
        }));
      });
    } else if (parsed.action && parsed.action == "pour") {
      if(activeKegerator !== null) {

      }
    } else if (parsed.action && parsed.action == "temps") {

      if(activeKegerator !== null) {
        activeKegerator.on('data', function(data) {
          ws.send(JSON.stringify({
            type: "temperature_update",
            data: data.toString('utf-8')
          }));
        });
        activeKegerator.write('temps\n');
      }
    }

  });

  ws.send('welcome!');
};
